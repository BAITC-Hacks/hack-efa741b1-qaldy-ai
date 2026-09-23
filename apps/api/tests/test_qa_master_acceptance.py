"""Behavioral acceptance probes for the Career Quest domain.

Synthetic cases deliberately vary only the input relevant to each assertion.
The T identifiers group related acceptance checks; browser behavior is covered
separately by the Playwright suite.
"""
import copy
import json
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.application.hr_service import HRFilters, HRService
from app.application.import_service import ImportService
from app.application.journey_service import JourneyService
from app.domain.models import ActivityRecord, CareerGoal, SkillGain
from app.infrastructure.dataset_loader import load_dataset, repository_dataset_dir
from app.infrastructure.llm_adapter import AIRecommendationItem, AIRecommendationPlan, OpenAIRecommendationAdapter
from app.infrastructure.sqlite_repository import SQLiteRepository


def scenario(*, design=2, speaking=0, gains=1, cap=5):
    bundle = load_dataset()
    source = bundle.employees['E0001']
    target = bundle.role_profiles[(source.role, 'Senior')]
    employee = replace(source, grade='Middle', career_goal=CareerGoal(source.role, 'Senior'),
                       skills={**target.required_skills, 'SK_SYSTEM_DESIGN': design, 'SK_PUBLIC_SPEAKING': speaking})
    prototype = next(iter(bundle.events.values()))
    def event(number, skill, kind, fmt):
        return replace(prototype, event_id=f'EV_{number}', title=f'Synthetic {skill} {kind}',
                       event_type=kind, event_format=fmt, mandatory=False, repeatable=False,
                       target_roles=frozenset({source.role}), target_grades=frozenset({'Middle'}),
                       develops_skills=(SkillGain(skill, gains, cap),), prerequisites={},
                       duration_hours=4, upcoming_sessions=(bundle.as_of_date,))
    events = [event(901, 'SK_PUBLIC_SPEAKING', 'workshop', 'offline'),
              event(902, 'SK_SYSTEM_DESIGN', 'course', 'self_paced'),
              event(903, 'SK_SYSTEM_DESIGN', 'mentoring', 'online'),
              event(904, 'SK_LEADERSHIP', 'mentoring', 'online')]
    return replace(bundle, employees={employee.employee_id: employee}, events={e.event_id: e for e in events}, history=())


def record(bundle, number, event, status):
    return ActivityRecord(f'QA-{number}', 'E0001', event,
                          bundle.as_of_date-timedelta(days=60), status,
                          100 if status == 'completed' else 0, 'manager' if status == 'declined' else 'self')


def test_T003_T011_T012_T013_first_middle_last_profile_fields():
    bundle = load_dataset()
    service = JourneyService(bundle)
    for employee_id in ('E0001', 'E0100', 'E0200'):
        journey = service.get_journey(employee_id)
        assert journey.employee == bundle.employees[employee_id]
        assert journey.employee.role and journey.employee.grade and journey.employee.tenure_months is not None
        assert {s.skill_id for s in journey.current_skills} == set(journey.employee.skills)
        assert all(0 <= s.level <= 5 for s in journey.current_skills)
        assert {(r.record_id, r.status, r.activity_date) for r in journey.activity_history} == {
            (r.record_id, r.status, r.activity_date) for r in bundle.history if r.employee_id == employee_id}


def test_T002_history_covers_24_calendar_months():
    bundle = load_dataset()
    assert len({(r.activity_date.year, r.activity_date.month) for r in bundle.history}) == 24
    assert min(r.activity_date for r in bundle.history).isoformat() == '2024-10-01'
    assert max(r.activity_date for r in bundle.history).isoformat() == '2026-09-30'


def test_T015_T016_T020_T021_T023_T024_T027_critical_gap_and_empty_history():
    bundle = scenario()
    journey = JourneyService(bundle).get_journey('E0001')
    assert not journey.activity_history
    assert journey.target_grade == 'Senior'
    assert {g.skill_id: (g.current_level, g.required_level, g.gap) for g in journey.skill_gaps} == {
        'SK_SYSTEM_DESIGN': (2, 4, 2), 'SK_PUBLIC_SPEAKING': (0, 2, 2)}
    assert 1 <= len(journey.recommendations) <= 3
    assert journey.recommendations[0].event_id in {'EV_902', 'EV_903'}
    assert 'EV_904' not in {r.event_id for r in journey.recommendations}
    skipped = replace(bundle, history=tuple(record(bundle, i, 'EV_901', 'no_show') for i in range(3)))
    after = JourneyService(skipped).get_journey('E0001')
    assert after.recommendations[0].event_id in {'EV_902', 'EV_903'}
    assert after.current_skills == journey.current_skills
    assert next(r.score for r in after.recommendations if r.event_id == 'EV_901') < next(
        r.score for r in journey.recommendations if r.event_id == 'EV_901')


def test_T025_T029_T030_history_changes_priority_without_changing_skills():
    bundle = scenario(speaking=2)
    before = JourneyService(bundle).get_journey('E0001')
    changed = replace(bundle, history=tuple(record(bundle, i, 'EV_902', 'declined') for i in range(3)) +
                      tuple(record(bundle, i+3, 'EV_904', 'completed') for i in range(3)))
    after = JourneyService(changed).get_journey('E0001')
    assert before.current_skills == after.current_skills
    assert after.recommendations[0].event_id == 'EV_903'
    scores_before = {r.event_id: r.score for r in before.recommendations}
    scores_after = {r.event_id: r.score for r in after.recommendations}
    assert scores_before != scores_after
    assert 'снижает приоритет' in next(r for r in after.recommendations if r.event_id == 'EV_902').reasons[2]


def test_T028_event_must_develop_actual_gap():
    bundle = scenario(speaking=2)
    bundle = replace(bundle, events={k: v for k, v in bundle.events.items() if k in {'EV_901', 'EV_904'}})
    journey = JourneyService(bundle).get_journey('E0001')
    assert journey.skill_gaps[0].skill_id == 'SK_SYSTEM_DESIGN'
    assert not journey.recommendations


def test_T031_T035_deterministic_reason_names_current_grade_and_four_factors():
    journey = JourneyService(scenario()).get_journey('E0001')
    for item in journey.recommendations:
        explanation = ' '.join(item.reasons)
        assert 'Middle' in explanation
        assert 'Senior' in explanation
        assert str(item.current_level) in explanation and str(item.required_level) in explanation
        assert 'История' in explanation


@pytest.mark.parametrize('omitted', ['career_goal', 'skill_gap', 'target_requirement', 'history'])
def test_T035_ai_must_not_omit_required_factor(omitted):
    journey = JourneyService(scenario()).get_journey('E0001')
    codes = ['career_goal', 'skill_gap', 'target_requirement', 'history']
    plan = tuple((r.event_id, tuple(c for c in codes if c != omitted)) for r in journey.recommendations)
    with pytest.raises(ValueError, match='evidence'):
        OpenAIRecommendationAdapter._validate_plan(journey, plan)


def test_T032_T033_T043_T044_T045_T046_T047_T048_T085_completion_caps_and_recalculation():
    bundle = scenario(design=3, speaking=2, gains=3, cap=4)
    service = JourneyService(bundle)
    before = service.get_journey('E0001')
    result = service.complete_activity('E0001', before.recommendations[0].event_id, 'qa-cap')
    old = {s.skill_id:s.level for s in before.current_skills}
    new = {s.skill_id:s.level for s in result.journey.current_skills}
    assert new['SK_SYSTEM_DESIGN'] == 4
    assert {k for k in old if old[k] != new[k]} == {'SK_SYSTEM_DESIGN'}
    assert result.changes[0].applied_gain == 1
    assert not result.journey.skill_gaps
    assert not result.journey.recommendations
    assert before.recommendations[0].projected_level == 4
    assert before.recommendations[0].required_level == 4
    assert all(level <= 5 for level in new.values())


def test_T081_T082_satisfied_requirements_do_not_create_deficits():
    journey = JourneyService(scenario(design=4, speaking=2)).get_journey('E0001')
    assert not journey.skill_gaps
    assert not journey.recommendations
    assert journey.progress.percentage == 100


def test_T017_no_invented_grade_after_lead():
    bundle = scenario()
    employee = replace(bundle.employees['E0001'], grade='Lead', career_goal=None)
    bundle = replace(bundle, employees={'E0001': employee})
    journey = JourneyService(bundle).get_journey('E0001')
    assert journey.target_grade == 'Lead' and journey.target_reason == 'no_target'


def test_T083_no_eligible_events_appears_in_hr():
    bundle = replace(scenario(), events={})
    service = JourneyService(bundle)
    assert not service.get_journey('E0001').recommendations
    assert [i['employee_id'] for i in HRService(service).uncovered_employees(HRFilters())['items']] == ['E0001']


def test_T084_zero_gain_never_promises_growth():
    journey = JourneyService(scenario(gains=0)).get_journey('E0001')
    assert journey.skill_gaps
    assert not journey.recommendations


def test_T014_T086_history_statuses_remain_distinct():
    bundle = scenario()
    history = tuple(record(bundle, i, 'EV_901', status) for i, status in enumerate(['completed','no_show','declined']))
    journey = JourneyService(replace(bundle, history=history)).get_journey('E0001')
    assert {r.status for r in journey.activity_history} == {'completed','no_show','declined'}


def test_T005_T010_T090_multilingual_batch_import_survives_restart(tmp_path):
    bundle = load_dataset()
    document = json.loads((repository_dataset_dir()/'employees.json').read_text(encoding='utf-8'))
    prototype = document['employees'][0]
    names = [('en','Synthetic Jury'), ('ru','Синтетический профиль'), ('kk','Ә Ғ Қ Ң Ө Ұ Ү Һ І')]
    document['employees'] = [dict(copy.deepcopy(prototype), employee_id=f'QA-{lang}', full_name=name, preferred_language=lang)
                             for lang,name in names]
    database = tmp_path/'unicode.db'
    service = ImportService(bundle, SQLiteRepository(database))
    validation = service.validate(document)
    assert validation.valid, validation.errors
    applied = service.apply(validation.validation_token, validation.package_hash, 'qa-unicode')
    assert applied.inserted_employees == 3
    restored = SQLiteRepository(database).list_imported_employees()
    assert {e['employee_id']: e['full_name'] for e in restored} == {f'QA-{lang}': name for lang,name in names}


def test_T006_imported_history_changes_new_profile_recommendation():
    bundle = load_dataset()
    document = json.loads((repository_dataset_dir()/'employees.json').read_text(encoding='utf-8'))
    document['employees'] = [dict(document['employees'][0], employee_id='QA-HISTORY')]
    service = ImportService(bundle, SQLiteRepository(':memory:'))
    valid = service.validate(document)
    assert valid.valid
    service.apply(valid.validation_token, valid.package_hash, 'qa-history-profile')
    before = JourneyService(bundle).get_journey('QA-HISTORY')
    event_id = before.recommendations[0].event_id
    csv_text = 'record_id,employee_id,event_id,date,due_date,status,completion_pct,score,feedback_rating,assigned_by\n'
    csv_text += ''.join(f'QA-H{i},QA-HISTORY,{event_id},2026-09-20,,declined,0,,,manager\n' for i in range(3))
    document['employees'] = []
    valid = service.validate(document, csv_text)
    assert valid.valid, valid.errors
    service.apply(valid.validation_token, valid.package_hash, 'qa-history-records')
    after = JourneyService(bundle).get_journey('QA-HISTORY')
    assert after.current_skills == before.current_skills
    assert len(after.activity_history) == 3
    before_score = next(r.score for r in before.recommendations if r.event_id == event_id)
    assert next(r.score for r in after.recommendations if r.event_id == event_id) < before_score


def test_T009_missing_field_and_invalid_skill_are_rejected_atomically():
    bundle = load_dataset()
    document = json.loads((repository_dataset_dir()/'employees.json').read_text(encoding='utf-8'))
    document['employees'] = [dict(document['employees'][0], employee_id='QA-INVALID')]
    del document['employees'][0]['role']
    document['employees'][0]['skills']['SK_PYTHON'] = 6
    repository = SQLiteRepository(':memory:')
    result = ImportService(bundle, repository).validate(document)
    assert not result.valid
    locations = {issue.location for issue in result.errors}
    assert '$.employees[0].role' in locations
    assert '$.employees[0].skills.SK_PYTHON' in locations
    assert not repository.list_imported_employees()
    assert 'QA-INVALID' not in bundle.employees


def test_T038_T039_model_cannot_supply_skill_or_level_facts():
    from pydantic import ValidationError
    for field, value in [('skill_id', 'SK_INVENTED'), ('required_level', 99), ('explanation', 'Invented promotion')]:
        with pytest.raises(ValidationError):
            AIRecommendationItem.model_validate({'event_id': 'EV_902', 'reason_codes':
                ['career_goal', 'skill_gap', 'target_requirement', 'history'], field: value})
