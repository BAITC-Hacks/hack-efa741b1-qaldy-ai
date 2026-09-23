from collections import Counter, defaultdict
from dataclasses import dataclass

from app.application.journey_service import JourneyService
from app.domain.models import ActivityRecord, Employee, Grade


@dataclass(frozen=True)
class HRFilters:
    department: str | None = None
    role: str | None = None
    grade: Grade | None = None


class HRService:
    """Read-only HR aggregates calculated from the active dataset snapshot."""

    def __init__(self, journey_service: JourneyService):
        self.journey_service = journey_service

    @property
    def dataset_version(self) -> str:
        return self.journey_service.bundle.dataset_version

    def skill_gaps(self, filters: HRFilters) -> dict[str, object]:
        employees = self._employees(filters)
        aggregates: dict[str, dict[str, object]] = {}
        for employee in employees:
            journey = self.journey_service.get_journey(employee.employee_id)
            for gap in journey.skill_gaps:
                row = aggregates.setdefault(
                    gap.skill_id,
                    {
                        "skill_id": gap.skill_id,
                        "name": gap.name,
                        "affected_employees": 0,
                        "total_gap": 0,
                        "critical_employees": 0,
                    },
                )
                row["affected_employees"] = int(row["affected_employees"]) + 1
                row["total_gap"] = int(row["total_gap"]) + gap.gap
                if gap.critical:
                    row["critical_employees"] = int(row["critical_employees"]) + 1

        items = sorted(
            aggregates.values(),
            key=lambda item: (
                -int(item["critical_employees"]),
                -int(item["affected_employees"]),
                -int(item["total_gap"]),
                str(item["skill_id"]),
            ),
        )
        for item in items:
            affected = int(item["affected_employees"])
            item["average_gap"] = round(int(item["total_gap"]) / affected, 2)
        return self._envelope(filters, len(employees), items)

    def participation(self, filters: HRFilters) -> dict[str, object]:
        employees = self._employees(filters)
        employee_ids = {item.employee_id for item in employees}
        records = [
            record
            for record in self._all_records(employee_ids)
            if record.employee_id in employee_ids
        ]
        by_status = Counter(record.status for record in records)
        by_type: dict[str, Counter[str]] = defaultdict(Counter)
        by_event: dict[str, Counter[str]] = defaultdict(Counter)
        for record in records:
            event = self.journey_service.bundle.events.get(record.event_id)
            if event is None:
                continue
            by_type[event.event_type][record.status] += 1
            by_event[event.event_id][record.status] += 1

        def participation_rows(
            grouped: dict[str, Counter[str]], *, event_labels: bool = False
        ) -> list[dict[str, object]]:
            rows: list[dict[str, object]] = []
            for key, statuses in grouped.items():
                total = sum(statuses.values())
                completed = statuses.get("completed", 0)
                row: dict[str, object] = {
                    "key": key,
                    "total": total,
                    "completed": completed,
                    "completion_rate": round(completed / total, 4) if total else 0,
                    "statuses": dict(sorted(statuses.items())),
                }
                if event_labels:
                    event = self.journey_service.bundle.events[key]
                    row["title"] = event.title
                rows.append(row)
            return sorted(rows, key=lambda item: (-int(item["total"]), str(item["key"])))

        result = self._envelope(filters, len(employees), [])
        result.update(
            {
                "total_records": len(records),
                "participating_employees": len({record.employee_id for record in records}),
                "statuses": dict(sorted(by_status.items())),
                "by_type": participation_rows(by_type),
                "by_event": participation_rows(by_event, event_labels=True),
            }
        )
        return result

    def uncovered_employees(self, filters: HRFilters) -> dict[str, object]:
        employees = self._employees(filters)
        items = []
        for employee in employees:
            journey = self.journey_service.get_journey(employee.employee_id)
            if journey.recommendations:
                continue
            items.append(
                {
                    "employee_id": employee.employee_id,
                    "full_name": employee.full_name,
                    "department": employee.department,
                    "role": employee.role,
                    "grade": employee.grade,
                    "primary_reason": journey.primary_reason or "catalog_gap",
                    "reason_counts": journey.reason_counts,
                    "gap_count": len(journey.skill_gaps),
                }
            )
        items.sort(key=lambda item: (str(item["primary_reason"]), str(item["employee_id"])))
        return self._envelope(filters, len(employees), items)

    def catalog_gaps(self, filters: HRFilters) -> dict[str, object]:
        employees = self._employees(filters)
        covered_skills = {
            gain.skill_id
            for event in self.journey_service.bundle.events.values()
            if not event.mandatory
            for gain in event.develops_skills
        }
        aggregate: dict[str, dict[str, object]] = {}
        for employee in employees:
            journey = self.journey_service.get_journey(employee.employee_id)
            for gap in journey.skill_gaps:
                if gap.skill_id in covered_skills:
                    continue
                row = aggregate.setdefault(
                    gap.skill_id,
                    {
                        "skill_id": gap.skill_id,
                        "name": gap.name,
                        "affected_employees": 0,
                        "critical_employees": 0,
                        "roles": set(),
                    },
                )
                row["affected_employees"] = int(row["affected_employees"]) + 1
                if gap.critical:
                    row["critical_employees"] = int(row["critical_employees"]) + 1
                roles = row["roles"]
                if isinstance(roles, set):
                    roles.add(journey.target_role)

        items = []
        for row in aggregate.values():
            items.append({**row, "roles": sorted(row["roles"])})
        items.sort(
            key=lambda item: (
                -int(item["critical_employees"]),
                -int(item["affected_employees"]),
                str(item["skill_id"]),
            )
        )
        return self._envelope(filters, len(employees), items)

    def _employees(self, filters: HRFilters) -> list[Employee]:
        return [
            employee
            for employee in sorted(
                self.journey_service.bundle.employees.values(),
                key=lambda item: item.employee_id,
            )
            if (filters.department is None or employee.department == filters.department)
            and (filters.role is None or employee.role == filters.role)
            and (filters.grade is None or employee.grade == filters.grade)
        ]

    def _all_records(self, employee_ids: set[str]) -> list[ActivityRecord]:
        # JourneyService owns the completion overlay, so use its de-duplicated view.
        records: list[ActivityRecord] = []
        for employee_id in employee_ids:
            records.extend(self.journey_service._employee_records(employee_id))
        return records

    def _envelope(
        self,
        filters: HRFilters,
        employee_count: int,
        items: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "dataset_version": self.dataset_version,
            "as_of_date": self.journey_service.bundle.as_of_date,
            "filters": {
                "department": filters.department,
                "role": filters.role,
                "grade": filters.grade,
            },
            "employee_count": employee_count,
            "items": items,
        }
