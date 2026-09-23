"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";

import styles from "./secondary-pages.module.css";

type Tab = { id: string; label: string };

function DemoNotice() {
  return <p className="demo-notice" role="note"><strong>Демо-экран.</strong> Профиль, показатели и действия здесь приведены для примера. Актуальную траекторию смотрите в разделе «Личная траектория».</p>;
}

function PageHeading({ title, subtitle, side }: { title: string; subtitle: string; side?: ReactNode }) {
  return (
    <div className={styles.headingRow}>
      <div className={styles.heading}>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {side}
    </div>
  );
}

function GoalCard({ compact = false }: { compact?: boolean }) {
  return (
    <div className={styles.goalCard} aria-label="Карьерная цель: Руководитель проекта, готовность 72 процента">
      <span className={styles.iconTile} aria-hidden="true">ЦЕЛЬ</span>
      <div><small>Ваша карьерная цель</small><strong>Руководитель проекта</strong></div>
      {!compact && <Ring value={72} />}
    </div>
  );
}

function Ring({ value, className = "" }: { value: number; className?: string }) {
  return (
    <span
      className={`${styles.ring} ${className}`}
      data-value={`${value}%`}
      style={{ "--value": value } as CSSProperties}
      aria-label={`${value} процентов`}
      aria-valuemax={100}
      aria-valuemin={0}
      aria-valuenow={value}
      role="progressbar"
    />
  );
}

function Panel({ children, className = "", padded = true }: { children: ReactNode; className?: string; padded?: boolean }) {
  return <section className={`${styles.panel} ${padded ? styles.panelPad : ""} ${className}`}>{children}</section>;
}

function SectionTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className={styles.sectionTitle}>
      <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
      {action}
    </div>
  );
}

function Tabs({ items, active, onChange, label }: { items: Tab[]; active: string; onChange: (id: string) => void; label: string }) {
  return (
    <div className={styles.tabs} role="tablist" aria-label={label}>
      {items.map((item) => (
        <button
          className={`${styles.tab} ${active === item.id ? styles.tabActive : ""}`}
          key={item.id}
          type="button"
          role="tab"
          aria-selected={active === item.id}
          onClick={() => onChange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function Progress({ value, label }: { value: number; label?: string }) {
  return (
    <div className={styles.progress} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value} aria-label={label}>
      <span style={{ width: `${value}%` }} />
    </div>
  );
}

function Tags({ items }: { items: string[] }) {
  return <div className={styles.tagRow}>{items.map((item) => <span className={styles.tag} key={item}>{item}</span>)}</div>;
}

function Notice({ message }: { message: string }) {
  if (!message) return null;
  return <p className={styles.toast} role="status">{message}</p>;
}

const learningTabs: Tab[] = [
  { id: "recommended", label: "Рекомендовано" },
  { id: "active", label: "В процессе" },
  { id: "saved", label: "Сохранённые" },
  { id: "done", label: "Завершённые" },
];

const courses = [
  { id: "stakeholders", title: "Управление стейкхолдерами", description: "Эффективная коммуникация и работа с ожиданиями", duration: "1,5 часа", skill: "Коммуникация", impact: 85, art: "ART" },
  { id: "facilitation", title: "Фасилитация встреч", description: "Проводите продуктивные встречи и воркшопы", duration: "2 часа", skill: "Коммуникация", impact: 75, art: "WORK" },
  { id: "finance", title: "Финансовое мышление", description: "Понимание финансовых показателей и решений", duration: "2,5 часа", skill: "Финансы", impact: 70, art: "DATA" },
  { id: "leadership", title: "Лидерство команды", description: "Развивайте и мотивируйте команду", duration: "2 часа", skill: "Лидерство", impact: 90, art: "TEAM" },
];

export function LearningPage() {
  const [tab, setTab] = useState("recommended");
  const [query, setQuery] = useState("");
  const [format, setFormat] = useState("all");
  const [skill, setSkill] = useState("all");
  const [saved, setSaved] = useState<string[]>(["finance"]);
  const [notice, setNotice] = useState("");

  const visibleCourses = useMemo(() => courses.filter((course) => {
    if (tab === "saved" && !saved.includes(course.id)) return false;
    if (tab === "active" && course.id !== "facilitation") return false;
    if (tab === "done" && course.id !== "stakeholders") return false;
    const matchesQuery = `${course.title} ${course.description} ${course.skill}`.toLowerCase().includes(query.toLowerCase());
    const matchesSkill = skill === "all" || course.skill === skill;
    return matchesQuery && matchesSkill && (format === "all" || format === "online");
  }), [format, query, saved, skill, tab]);

  function toggleSaved(id: string) {
    setSaved((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id]);
  }

  return (
    <main className={styles.page}>
      <DemoNotice />
      <PageHeading title="Обучение" subtitle="Учитесь тому, что приближает к карьерной цели" side={<GoalCard />} />
      <Notice message={notice} />
      <div className={styles.learningLayout}>
        <div className={styles.learningMain}>
          <Panel className={styles.currentCourse} padded={false}>
            <div className={styles.courseArt} aria-hidden="true">▶</div>
            <div className={styles.currentInfo}>
              <span className={styles.status}>В процессе</span>
              <h2>Стратегическое мышление</h2>
              <p>4 из 7 модулей · 60%</p>
              <Progress value={60} label="Прогресс курса Стратегическое мышление" />
              <div className={styles.meta}><span>Онлайн-курс</span><span>2 часа</span><span>+250 XP</span></div>
            </div>
            <button className={styles.primaryButton} type="button" onClick={() => setNotice("Обучение продолжено с модуля 5")}>Продолжить обучение →</button>
          </Panel>

          <Panel>
            <Tabs items={learningTabs} active={tab} onChange={setTab} label="Разделы обучения" />
            <div className={styles.filters} style={{ marginTop: 14 }}>
              <input className={styles.search} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск курсов, навыков, тем..." aria-label="Поиск курсов" />
              <select className={styles.select} value={format} onChange={(event) => setFormat(event.target.value)} aria-label="Формат курса">
                <option value="all">Формат: все</option><option value="online">Онлайн</option><option value="offline">Очно</option>
              </select>
              <select className={styles.select} aria-label="Длительность курса"><option>Длительность: все</option><option>До 2 часов</option><option>Более 2 часов</option></select>
              <select className={styles.select} value={skill} onChange={(event) => setSkill(event.target.value)} aria-label="Навык курса">
                <option value="all">Навык: все</option><option>Коммуникация</option><option>Финансы</option><option>Лидерство</option>
              </select>
            </div>
            <SectionTitle title="Для роли «Руководитель проекта»" subtitle="Курсы, которые помогут развить ключевые навыки" />
            {visibleCourses.length ? (
              <div className={styles.courseGrid}>
                {visibleCourses.map((course, index) => (
                  <article className={styles.courseCard} key={course.id}>
                    <div className={`${styles.courseArt} ${index % 3 === 1 ? styles.courseArtAlt : index % 3 === 2 ? styles.courseArtGold : ""}`}>{course.art}</div>
                    <button className={`${styles.bookmark} ${saved.includes(course.id) ? styles.bookmarkSaved : ""}`} type="button" aria-label={saved.includes(course.id) ? `Удалить ${course.title} из сохранённых` : `Сохранить ${course.title}`} aria-pressed={saved.includes(course.id)} onClick={() => toggleSaved(course.id)}>⌑</button>
                    <h3>{course.title}</h3><p>{course.description}</p>
                    <div className={styles.meta}><span>{course.duration}</span><span>Онлайн</span></div>
                    <Tags items={[course.skill]} />
                    <div className={styles.impact}><span>+{course.impact}% влияние на цель</span><span>+200 XP</span></div>
                  </article>
                ))}
              </div>
            ) : (
              <div className={styles.empty}><div><h3>Курсы не найдены</h3><p>Измените запрос или сбросьте фильтры.</p><button className={styles.ghostButton} type="button" onClick={() => { setQuery(""); setFormat("all"); setSkill("all"); setTab("recommended"); }}>Сбросить фильтры</button></div></div>
            )}
          </Panel>
        </div>

        <aside className={styles.learningAside} aria-label="Дополнительная информация об обучении">
          <Panel>
            <SectionTitle title="Ближайшее обучение" />
            <div className={styles.stack}>
              {["15 сен · Фасилитация встреч", "17 сен · Финансовое мышление"].map((item) => <div className={styles.listItem} key={item}><span className={styles.iconTile}>КАЛ</span><div><strong>{item}</strong><small>10:00 · Онлайн</small></div></div>)}
            </div>
            <button className={styles.ghostButton} style={{ width: "100%", marginTop: 10 }} type="button" onClick={() => setNotice("Событие добавлено в демо-календарь")}>Добавить в календарь</button>
          </Panel>
          <Panel>
            <SectionTitle title="Мои сертификаты" />
            <div className={styles.stack}>{["Эффективная коммуникация", "Управление проектами", "Аналитическое мышление"].map((item) => <div className={styles.listItem} key={item}><span className={styles.iconTile}>CERT</span><div><strong>{item}</strong><small>Завершён · 2026</small></div></div>)}</div>
          </Panel>
          <Panel className={styles.aiCard}>
            <SectionTitle title="Почему это обучение?" />
            <p>AI сопоставил навыки для роли руководителя проекта с вашим профилем. Подборка закрывает самые важные разрывы: коммуникацию, финансы и лидерство.</p>
          </Panel>
        </aside>
      </div>
    </main>
  );
}

const opportunityTabs: Tab[] = [
  { id: "all", label: "Для вас (4)" },
  { id: "project", label: "Проекты (12)" },
  { id: "rotation", label: "Ротации (6)" },
  { id: "vacancy", label: "Вакансии (8)" },
  { id: "mentor", label: "Наставничество (5)" },
];

const opportunities = [
  { id: "lead", type: "project", title: "Руководитель проектного потока", kind: "Проектная роль", unit: "Департамент цифровых решений", duration: "6–12 месяцев", location: "Алматы / Гибрид", match: 78, skills: ["Управление командой", "Agile"] },
  { id: "digital", type: "project", title: "Проект цифровой трансформации", kind: "Внутренний проект", unit: "Департамент IT", duration: "3–6 месяцев", location: "Гибрид", match: 82, skills: ["Аналитика данных", "Бизнес-процессы"] },
  { id: "rotation", type: "rotation", title: "Временная ротация в продуктовую команду", kind: "Внутренняя ротация", unit: "Департамент розничного бизнеса", duration: "3 месяца", location: "Алматы / Гибрид", match: 76, skills: ["Продуктовое мышление", "Работа с данными"] },
  { id: "mentor", type: "mentor", title: "Наставник по лидерству", kind: "Наставничество", unit: "Корпоративный университет", duration: "3–6 месяцев", location: "Удалённо", match: 68, skills: ["Лидерство", "Коммуникация"] },
];

export function OpportunitiesPage() {
  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");
  const [format, setFormat] = useState("all");
  const [direction, setDirection] = useState("all");
  const [readiness, setReadiness] = useState("all");
  const [saved, setSaved] = useState<string[]>([]);
  const [applied, setApplied] = useState<string[]>([]);
  const [notice, setNotice] = useState("");

  const filtered = useMemo(() => opportunities.filter((item) => {
    const matchesTab = tab === "all" || item.type === tab;
    const matchesQuery = `${item.title} ${item.unit} ${item.skills.join(" ")}`.toLowerCase().includes(query.toLowerCase());
    const matchesDirection = direction === "all" || item.skills.some((skill) => skill.toLowerCase().includes(direction));
    const matchesReadiness = readiness === "all" || (readiness === "high" ? item.match >= 80 : item.match < 80);
    const matchesFormat = format === "all" || item.location.toLowerCase().includes(format);
    return matchesTab && matchesQuery && matchesDirection && matchesReadiness && matchesFormat;
  }), [direction, format, query, readiness, tab]);

  function apply(id: string, title: string) {
    if (applied.includes(id)) return;
    setApplied((items) => [...items, id]);
    setNotice(`Отклик на «${title}» отправлен`);
  }

  function toggleSaved(id: string, title: string) {
    const isSaved = saved.includes(id);
    setSaved((items) => isSaved ? items.filter((item) => item !== id) : [...items, id]);
    setNotice(isSaved ? `«${title}» удалено из сохранённых` : `«${title}» сохранено`);
  }

  return (
    <main className={styles.page}>
      <DemoNotice />
      <PageHeading title="Возможности" subtitle="Реальные шаги к следующей карьерной роли" side={<GoalCard compact />} />
      <Panel>
        <div className={styles.filters}>
          <select className={styles.select} value={format} onChange={(event) => setFormat(event.target.value)} aria-label="Формат возможности"><option value="all">Все форматы</option><option value="гибрид">Гибрид</option><option value="удал">Удалённо</option></select>
          <select className={styles.select} value={direction} onChange={(event) => setDirection(event.target.value)} aria-label="Направление возможности"><option value="all">Все направления</option><option value="аналитика">Аналитика</option><option value="лидерство">Лидерство</option></select>
          <select className={styles.select} aria-label="Длительность возможности"><option>Любая длительность</option><option>До 3 месяцев</option><option>3–6 месяцев</option></select>
          <select className={styles.select} value={readiness} onChange={(event) => setReadiness(event.target.value)} aria-label="Готовность к возможности"><option value="all">Любая готовность</option><option value="high">80% и выше</option><option value="medium">До 80%</option></select>
        </div>
        <input className={styles.search} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск по возможностям..." aria-label="Поиск возможностей" />
      </Panel>
      <Notice message={notice} />

      <div className={styles.opportunityHero} style={{ marginTop: 12 }}>
        <Panel className={styles.recommendation}>
          <div>
            <span className={styles.status}>Рекомендуем для вас</span>
            <h2>Ротация в PMO</h2>
            <p>Участвуйте в ключевых инициативах трансформации банка, получите опыт управления проектами и расширьте межфункциональные связи.</p>
            <Tags items={["Управление проектами", "Коммуникация", "Аналитическое мышление"]} />
            <div className={styles.meta} style={{ marginTop: 14 }}><span>6 месяцев</span><span>Кросс-функциональная команда</span><span>Алматы / Гибрид</span></div>
          </div>
          <div className={styles.metric}><Ring value={86} /><strong>Совпадение</strong><br /><small>Отличное соответствие профилю</small></div>
          <div className={styles.metric}><Ring value={72} /><strong>Готовность</strong><br /><small>Большинство навыков уже есть</small></div>
        </Panel>
        <aside className={styles.opportunityAside}>
          <Panel>
            <SectionTitle title="Что нужно улучшить" subtitle="2 навыка для большей готовности" />
            <div className={styles.stack}><div className={styles.listItem}><span className={styles.iconTile}>01</span><div><strong>Управление стейкхолдерами</strong><small>Приоритетный курс</small></div></div><div className={styles.listItem}><span className={styles.iconTile}>02</span><div><strong>Финансовый анализ проектов</strong><small>Рекомендуем обучение</small></div></div></div>
          </Panel>
          <Panel className={styles.aiCard}><SectionTitle title="Почему подходит" subtitle="AI-рекомендация" /><p>Ваш опыт в аналитике, коммуникации и интерес к трансформации совпадают с задачами ротации. Это логичный шаг к роли руководителя проекта.</p></Panel>
        </aside>
      </div>

      <div style={{ marginTop: 12 }}><Tabs items={opportunityTabs} active={tab} onChange={setTab} label="Категории возможностей" /></div>
      {filtered.length ? (
        <div className={styles.opportunityGrid}>
          {filtered.map((item) => (
            <article className={styles.opportunityCard} key={item.id}>
              <Ring value={item.match} className={styles.miniRing} />
              <span className={styles.status}>{item.kind}</span>
              <h3>{item.title}</h3><p>{item.unit}</p>
              <div className={styles.meta}><span>{item.duration}</span><span>{item.location}</span></div>
              <p style={{ marginTop: 12 }}>Ключевые навыки</p><Tags items={item.skills} />
              <div className={styles.opportunityActions}>
                <button className={styles.primaryButton} disabled={applied.includes(item.id)} type="button" onClick={() => apply(item.id, item.title)}>{applied.includes(item.id) ? "Отклик отправлен" : "Откликнуться"}</button>
                <button className={styles.ghostButton} type="button" aria-pressed={saved.includes(item.id)} onClick={() => toggleSaved(item.id, item.title)}>{saved.includes(item.id) ? "Сохранено" : "Сохранить"}</button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Panel className={styles.empty}><div><h3>Подходящих возможностей пока нет</h3><p>Измените сочетание фильтров, чтобы увидеть больше вариантов.</p><button className={styles.ghostButton} type="button" onClick={() => { setFormat("all"); setDirection("all"); setReadiness("all"); setQuery(""); setTab("all"); }}>Сбросить фильтры</button></div></Panel>
      )}
    </main>
  );
}

const members = [
  { initials: "АС", name: "Анна Смирнова", role: "Аналитик", busy: false },
  { initials: "ТК", name: "Тимур Касенов", role: "Продакт-менеджер", busy: false },
  { initials: "АН", name: "Айгерим Нургали", role: "UX/UI дизайнер", busy: true },
  { initials: "ДВ", name: "Дмитрий Волков", role: "Разработчик", busy: false },
  { initials: "МК", name: "Мария Коваленко", role: "Маркетолог", busy: true },
];

const skillProgress = [
  ["Аналитика", 80, "4/5"], ["Коммуникация", 100, "5/5"], ["Управление проектами", 60, "3/5"], ["Креативное мышление", 60, "3/5"], ["Работа с данными", 80, "4/5"],
] as const;

export function TeamPage() {
  const [role, setRole] = useState("Аналитика и презентация");
  const [draftRole, setDraftRole] = useState(role);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const selectRef = useRef<HTMLSelectElement>(null);

  useEffect(() => {
    if (!dialogOpen) return;
    selectRef.current?.focus();
    function handleKey(event: KeyboardEvent) { if (event.key === "Escape") setDialogOpen(false); }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [dialogOpen]);

  function saveRole() {
    setRole(draftRole);
    setDialogOpen(false);
    setNotice("Роль в командной миссии обновлена");
  }

  return (
    <main className={styles.page}>
      <DemoNotice />
      <PageHeading title="Команда" subtitle="Развивайтесь вместе через реальные задачи" side={<div className={styles.banner}><span className={styles.iconTile}>TEAM</span><div><strong>Сильная команда делает больше</strong><small>Обменивайтесь опытом и помогайте друг другу</small></div></div>} />
      <Notice message={notice} />
      <div className={styles.teamGrid}>
        <Panel className={styles.mission}>
          <SectionTitle title="Текущая командная миссия" />
          <div className={styles.listItem}><span className={styles.iconTile}>CASE</span><div style={{ flex: 1 }}><strong>Клиентский кейс</strong><small>Командное задание · Управление стейкхолдерами</small><div style={{ marginTop: 10 }}><Progress value={60} label="Прогресс миссии" /></div></div><button className={styles.primaryButton} type="button" onClick={() => setNotice("Открыта командная миссия «Клиентский кейс»")}>Перейти →</button></div>
          <div className={styles.meta} style={{ marginTop: 14 }}><span>Цель: подготовить решение</span><span>Срок: 15 окт. 2026</span><span>+200 XP всей команде</span></div>
        </Panel>

        <Panel className={styles.roleCard}>
          <SectionTitle title="Моя роль в миссии" action={<button className={styles.linkButton} type="button" onClick={() => { setDraftRole(role); setDialogOpen(true); }}>Редактировать</button>} />
          <span className={styles.iconTile}>ROLE</span><h3>{role}</h3><p>Анализ данных, подготовка выводов и финальной презентации для клиента.</p>
        </Panel>

        <Panel>
          <SectionTitle title="Прогресс команды по навыкам" />
          {skillProgress.map(([name, value, score]) => <div className={styles.skillRow} key={name}><span>{name}</span><Progress value={value} label={`${name}: ${score}`} /><strong>{score}</strong></div>)}
        </Panel>

        <Panel className={styles.members}>
          <SectionTitle title="Участники команды" subtitle="5 участников" />
          <div className={styles.memberGrid}>{members.map((member) => <div className={styles.member} key={member.name}><span className={`${styles.avatar} ${member.busy ? styles.avatarBusy : ""}`}>{member.initials}</span><strong>{member.name}</strong><small>{member.role}</small><span className={`${styles.status} ${member.busy ? styles.statusWarm : ""}`} style={{ margin: "7px auto 0" }}>{member.busy ? "В работе" : "Активно"}</span></div>)}</div>
        </Panel>

        <Panel>
          <SectionTitle title="Запросы о помощи" action={<button className={styles.linkButton} type="button">Смотреть все</button>} />
          <div className={styles.stack}>{[["Дмитрий Волков", "Нужен взгляд на структуру презентации"], ["Айгерим Нургали", "Кто может проверить данные по рынку?"], ["Тимур Касенов", "Нужна обратная связь по прототипу"]].map(([name, text]) => <div className={styles.listItem} key={name}><span className={styles.avatar} style={{ width: 38, height: 38, margin: 0 }}>{name.split(" ").map((part) => part[0]).join("")}</span><div><strong>{name}</strong><small>{text}</small></div></div>)}</div>
        </Panel>

        <Panel>
          <SectionTitle title="Наставники" action={<button className={styles.linkButton} type="button">Все наставники</button>} />
          <div className={styles.stack}>{[["Ерлан Сейтжанов", "Руководитель продукта"], ["Мадина Ибрагимова", "Директор по маркетингу"]].map(([name, title]) => <div className={styles.listItem} key={name}><span className={styles.avatar} style={{ width: 42, height: 42, margin: 0 }}>{name.split(" ").map((part) => part[0]).join("")}</span><div><strong>{name}</strong><small>{title} · доступен на неделе</small></div></div>)}</div>
        </Panel>

        <Panel>
          <SectionTitle title="Совместные квесты" />
          <div className={styles.questGrid}>{[["Лидерство в действии", 25], ["Инновационное решение", 0], ["Эффективные коммуникации", 50]].map(([title, progress]) => <article className={styles.questCard} key={String(title)}><span className={styles.iconTile}>XP</span><h3>{title}</h3><Progress value={Number(progress)} label={`Прогресс: ${progress}%`} /><p>+200 XP</p></article>)}</div>
        </Panel>

        <Panel className={styles.aiCard}>
          <SectionTitle title="Кого подключить (AI)" />
          <p>Для миссии полезно подключить экспертов по финансовому анализу и работе с клиентами.</p><Tags items={["Финансовый анализ", "Работа с клиентами"]} /><button className={styles.ghostButton} style={{ marginTop: 13 }} type="button" onClick={() => setNotice("AI подобрал 3 подходящих коллеги")}>Найти коллег →</button>
        </Panel>

        <Panel>
          <SectionTitle title="Спасибо за вклад" />
          <div className={styles.stack}><div className={styles.listItem}><span className={styles.iconTile}>+1</span><div><strong>Айгерим благодарит Тимура</strong><small>«Спасибо за быструю помощь с данными!»</small></div></div><div className={styles.listItem}><span className={styles.iconTile}>+1</span><div><strong>Дмитрий благодарит Марию</strong><small>«Классные идеи для презентации!»</small></div></div></div>
        </Panel>
      </div>

      {dialogOpen && (
        <div className={styles.dialogBackdrop} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setDialogOpen(false); }}>
          <div className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="role-dialog-title">
            <h2 id="role-dialog-title">Изменить роль в миссии</h2>
            <p>Выберите вклад, который лучше всего отражает ваши задачи. Изменение увидят участники команды.</p>
            <label htmlFor="team-role">Роль</label>
            <select ref={selectRef} id="team-role" className={styles.select} value={draftRole} onChange={(event) => setDraftRole(event.target.value)}>
              <option>Аналитика и презентация</option><option>Координация команды</option><option>Исследование клиента</option><option>Фасилитация</option>
            </select>
            <div className={styles.dialogActions}><button className={styles.ghostButton} type="button" onClick={() => setDialogOpen(false)}>Отмена</button><button className={styles.primaryButton} type="button" onClick={saveRole}>Сохранить</button></div>
          </div>
        </div>
      )}
    </main>
  );
}

const resourceTabs: Tab[] = [
  { id: "all", label: "Все" }, { id: "course", label: "Курсы" }, { id: "video", label: "Видео" }, { id: "article", label: "Статьи" }, { id: "template", label: "Шаблоны" }, { id: "case", label: "Кейсы" },
];

const resources = [
  { id: "plan", type: "template", title: "Шаблон проектного плана", meta: "Шаблон · 15 мин", topic: "Управление проектами", code: "XLS" },
  { id: "checklist", type: "article", title: "Чек-лист фасилитации", meta: "Статья · 10 мин", topic: "Коммуникация", code: "DOC" },
  { id: "talks", type: "video", title: "Видео: сложные переговоры", meta: "Видео · 25 мин", topic: "Переговоры", code: "PLAY" },
  { id: "digital-case", type: "case", title: "Кейс цифровой трансформации", meta: "Кейс · 20 мин", topic: "Стратегическое мышление", code: "CASE" },
  { id: "feedback", type: "article", title: "Гайд по обратной связи", meta: "Статья · 12 мин", topic: "Лидерство", code: "GUIDE" },
  { id: "stakeholder", type: "course", title: "Управление стейкхолдерами", meta: "Курс · 40 мин", topic: "Управление проектами", code: "EDU" },
];

export function LibraryPage() {
  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");
  const [topic, setTopic] = useState("all");
  const [duration, setDuration] = useState("all");
  const [saved, setSaved] = useState<string[]>(["plan", "digital-case"]);
  const [recent, setRecent] = useState<string[]>(["talks", "stakeholder"]);
  const [notice, setNotice] = useState("");

  const filteredResources = useMemo(() => resources.filter((resource) => {
    const matchesTab = tab === "all" || resource.type === tab;
    const matchesQuery = `${resource.title} ${resource.topic} ${resource.meta}`.toLowerCase().includes(query.toLowerCase());
    const matchesTopic = topic === "all" || resource.topic === topic;
    const minutes = Number(resource.meta.match(/\d+/)?.[0] ?? 0);
    const matchesDuration = duration === "all" || (duration === "short" ? minutes <= 15 : minutes > 15);
    return matchesTab && matchesQuery && matchesTopic && matchesDuration;
  }), [duration, query, tab, topic]);

  function openResource(resource: (typeof resources)[number]) {
    setRecent((items) => [resource.id, ...items.filter((id) => id !== resource.id)].slice(0, 4));
    setNotice(`Материал «${resource.title}» открыт в демо-режиме`);
  }

  function toggleResource(id: string) {
    setSaved((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id]);
  }

  const recentResources = recent.map((id) => resources.find((resource) => resource.id === id)).filter((resource): resource is (typeof resources)[number] => Boolean(resource));
  const savedResources = saved.map((id) => resources.find((resource) => resource.id === id)).filter((resource): resource is (typeof resources)[number] => Boolean(resource));

  return (
    <main className={styles.page}>
      <DemoNotice />
      <PageHeading title="Библиотека" subtitle="Материалы для работы и карьерного развития" />
      <input className={`${styles.search} ${styles.librarySearch}`} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Найти материал, навык или тему" aria-label="Поиск материалов" />
      <div className={styles.libraryToolbar}>
        <Tabs items={resourceTabs} active={tab} onChange={setTab} label="Типы материалов" />
        <select className={styles.select} value={topic} onChange={(event) => setTopic(event.target.value)} aria-label="Тема материала"><option value="all">Тема: все</option><option>Управление проектами</option><option>Коммуникация</option><option>Лидерство</option></select>
        <select className={styles.select} aria-label="Формат материала"><option>Формат: все</option><option>Текст</option><option>Видео</option></select>
        <select className={styles.select} value={duration} onChange={(event) => setDuration(event.target.value)} aria-label="Длительность материала"><option value="all">Длительность: все</option><option value="short">До 15 минут</option><option value="long">Более 15 минут</option></select>
      </div>
      <Notice message={notice} />

      <div className={styles.libraryLayout}>
        <div className={styles.libraryMain}>
          <Panel>
            <SectionTitle title="Для роли «Руководитель проекта»" subtitle="Практические материалы для текущей роли" action={<button className={styles.linkButton} type="button">Смотреть все →</button>} />
            {filteredResources.length ? (
              <div className={styles.resourceGrid}>{filteredResources.slice(0, 5).map((resource) => <article className={styles.resourceCard} key={resource.id}><div className={styles.resourceArt}>{resource.code}</div><button className={`${styles.bookmark} ${saved.includes(resource.id) ? styles.bookmarkSaved : ""}`} type="button" aria-label={saved.includes(resource.id) ? `Удалить ${resource.title} из сохранённых` : `Сохранить ${resource.title}`} aria-pressed={saved.includes(resource.id)} onClick={() => toggleResource(resource.id)}>⌑</button><h3>{resource.title}</h3><p>{resource.meta}</p><Tags items={[resource.topic]} /><button className={styles.linkButton} style={{ marginTop: 10 }} type="button" onClick={() => openResource(resource)}>Открыть материал →</button></article>)}</div>
            ) : (
              <div className={styles.empty}><div><h3>Ничего не найдено</h3><p>Попробуйте другой запрос или сбросьте выбранные фильтры.</p><button className={styles.ghostButton} type="button" onClick={() => { setQuery(""); setTab("all"); setTopic("all"); setDuration("all"); }}>Сбросить фильтры</button></div></div>
            )}
          </Panel>

          <Panel className={styles.aiCard}>
            <SectionTitle title="Подборка недели" subtitle="AI собрал актуальные материалы на основе вашей роли и целей" action={<button className={styles.ghostButton} type="button" onClick={() => setNotice("AI-подборка обновлена")}>Другие рекомендации →</button>} />
            <div className={styles.weeklyGrid}>{resources.slice(1, 4).map((resource) => <article className={styles.resourceCard} key={`week-${resource.id}`}><span className={styles.iconTile}>{resource.code}</span><h3>{resource.title}</h3><p>{resource.meta}</p><div className={styles.impact}>Актуально для карьерной цели</div></article>)}</div>
          </Panel>
        </div>

        <aside className={styles.libraryAside} aria-label="Сохранённые и популярные материалы">
          <Panel>
            <SectionTitle title="Сохранённые" action={<button className={styles.linkButton} type="button" onClick={() => setTab("all")}>Смотреть все</button>} />
            <div className={styles.stack}>{savedResources.length ? savedResources.map((resource) => <button className={styles.listItem} style={{ width: "100%", textAlign: "left" }} type="button" key={resource.id} onClick={() => openResource(resource)}><span className={styles.iconTile}>{resource.code}</span><div><strong>{resource.title}</strong><small>{resource.meta}</small></div></button>) : <p>Сохранённых материалов пока нет.</p>}</div>
          </Panel>
          <Panel>
            <SectionTitle title="Недавно просмотренные" />
            <div className={styles.stack}>{recentResources.map((resource) => <button className={styles.listItem} style={{ width: "100%", textAlign: "left" }} type="button" key={`recent-${resource.id}`} onClick={() => openResource(resource)}><span className={styles.iconTile}>{resource.code}</span><div><strong>{resource.title}</strong><small>{resource.meta}</small></div></button>)}</div>
          </Panel>
          <Panel>
            <SectionTitle title="Популярно в вашей роли" />
            <div className={styles.stack}>{["Управление стейкхолдерами", "Стратегическое планирование", "Построение команды"].map((title, index) => <div className={styles.listItem} key={title}><span className={styles.iconTile}>{index + 1}</span><div><strong>{title}</strong><small>{index === 0 ? "Курс · 40 мин" : "Статья · 15 мин"}</small></div></div>)}</div>
          </Panel>
        </aside>
      </div>
    </main>
  );
}

const portfolioTabs: Tab[] = [
  { id: "all", label: "Все" }, { id: "certificate", label: "Сертификаты" }, { id: "project", label: "Проекты" }, { id: "review", label: "Отзывы" }, { id: "case", label: "Кейсы" },
];

const portfolioItems = [
  { id: "analysis", type: "project", title: "Анализ клиентской базы Q1 2025", meta: "Проект · PDF · 12 мар. 2025", code: "PDF" },
  { id: "dashboard", type: "project", title: "Дашборд финансовых метрик", meta: "Проект · XLSX · 3 фев. 2025", code: "XLS" },
  { id: "review", type: "review", title: "Отзыв руководителя «Высокая ответственность»", meta: "Отзыв · 28 янв. 2025", code: "MSG" },
  { id: "process", type: "case", title: "Кейс по оптимизации процессов", meta: "Кейс · PDF · 15 дек. 2024", code: "CASE" },
];

export function ProfilePage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [portfolioTab, setPortfolioTab] = useState("all");
  const [profileVisibility, setProfileVisibility] = useState("team");
  const [sectionsVisibility, setSectionsVisibility] = useState("skills");
  const [editOpen, setEditOpen] = useState(false);
  const [name, setName] = useState("Анна Смирнова");
  const [draftName, setDraftName] = useState(name);
  const [city, setCity] = useState("Алматы");
  const [draftCity, setDraftCity] = useState(city);
  const [notice, setNotice] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function closeMenu(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false);
    }
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") { setMenuOpen(false); setEditOpen(false); }
    }
    document.addEventListener("mousedown", closeMenu);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", closeMenu); document.removeEventListener("keydown", escape); };
  }, []);

  const visiblePortfolio = portfolioItems.filter((item) => portfolioTab === "all" || item.type === portfolioTab);

  function saveProfile() {
    setName(draftName.trim() || name);
    setCity(draftCity.trim() || city);
    setEditOpen(false);
    setNotice("Профиль обновлён");
  }

  return (
    <main className={styles.page}>
      <DemoNotice />
      <div className={styles.headingRow}>
        <div className={styles.heading}><h1>Профиль и достижения</h1><p>Ваш подтверждённый карьерный капитал</p></div>
        <div className={styles.profileMenuWrap} ref={menuRef}>
          <button className={styles.menuButton} type="button" aria-haspopup="menu" aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>Меню профиля ▾</button>
          {menuOpen && <div className={styles.menu} role="menu"><button role="menuitem" type="button" onClick={() => setMenuOpen(false)}>Профиль и достижения</button><button role="menuitem" type="button" onClick={() => { setMenuOpen(false); setNotice("Настройки открыты в демо-режиме"); }}>Настройки</button><button role="menuitem" type="button" onClick={() => { setMenuOpen(false); setNotice("Выход недоступен в демо-режиме"); }}>Выйти</button></div>}
        </div>
      </div>
      <Notice message={notice} />

      <div className={styles.profileTop}>
        <Panel className={styles.profileCard}>
          <span className={`${styles.avatar} ${styles.profileAvatar}`}>АС</span>
          <div><h1>{name}</h1><p>Аналитик</p><p>Финансы · {city}</p></div>
          <button className={styles.ghostButton} type="button" onClick={() => { setDraftName(name); setDraftCity(city); setEditOpen(true); }}>Редактировать профиль</button>
        </Panel>
        <Panel>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}><span className={styles.iconTile}>ЦЕЛЬ</span><div><small>Карьерная цель</small><strong style={{ display: "block", marginTop: 3 }}>Руководитель проекта</strong></div><Ring value={72} /></div>
          <button className={styles.ghostButton} style={{ marginTop: 10 }} type="button" onClick={() => setNotice("Переход к выбору карьерной цели")}>Изменить цель →</button>
        </Panel>
      </div>

      <div className={styles.profileGrid}>
        <Panel>
          <SectionTitle title="Мой прогресс" />
          <div className={styles.statRow}><div className={styles.stat}><strong>7</strong><small>уровень</small></div><div className={styles.stat}><strong>2 450</strong><small>из 3 000 XP</small></div><div className={styles.stat}><strong>12</strong><small>квестов</small></div></div>
          <p className={styles.statusWarm} style={{ margin: "14px 0 0", padding: 9, borderRadius: 8 }}>Серия развития: 4 недели</p>
        </Panel>

        <Panel>
          <SectionTitle title="Ключевые навыки" action={<button className={styles.linkButton} type="button">Управление навыками</button>} />
          {[["Аналитическое мышление", 82, "4"], ["Коммуникация", 68, "3"], ["Управление проектами", 65, "3"], ["Работа с данными", 84, "4"], ["Лидерство", 48, "2"]].map(([skillName, value, level]) => <div className={styles.skillRow} key={String(skillName)}><span>{skillName}</span><Progress value={Number(value)} label={`${skillName}: уровень ${level}`} /><strong>ур. {level}</strong></div>)}
        </Panel>

        <Panel>
          <SectionTitle title="Достижения" action={<button className={styles.linkButton} type="button">Смотреть все</button>} />
          <div className={styles.achievementGrid}>{[["Первый проект", "Завершён первый реальный проект"], ["Наставник", "Помощь 5 коллегам"], ["30 дней развития", "Непрерывная активность"], ["Командный игрок", "Высокая оценка"], ["Эксперт по аналитике", "Подтверждён сертификатом"]].map(([title, text], index) => <article className={styles.achievement} key={title}><span className={styles.medal}>{index + 1}</span><strong>{title}</strong><small>{text}</small></article>)}</div>
        </Panel>

        <Panel className={styles.profileWide}>
          <SectionTitle title="Портфолио" action={<button className={styles.linkButton} type="button" onClick={() => setNotice("Форма добавления материала открыта в демо-режиме")}>Добавить материал →</button>} />
          <Tabs items={portfolioTabs} active={portfolioTab} onChange={setPortfolioTab} label="Типы материалов портфолио" />
          <div className={styles.portfolioGrid} style={{ marginTop: 10 }}>{visiblePortfolio.length ? visiblePortfolio.map((item) => <article className={styles.portfolioCard} key={item.id}><span className={styles.iconTile}>{item.code}</span><h3>{item.title}</h3><p>{item.meta}</p></article>) : <p>В этом разделе пока нет материалов.</p>}</div>
        </Panel>

        <Panel>
          <SectionTitle title="История развития" action={<button className={styles.linkButton} type="button">Смотреть все</button>} />
          <div className={styles.timeline}>{[["Сегодня", "Завершён курс «Стратегическое мышление»"], ["12 мар. 2025", "Завершён проект «Анализ клиентской базы»"], ["3 фев. 2025", "Получен значок «Наставник»"], ["15 янв. 2025", "Повышен навык «Работа с данными»"]].map(([date, event]) => <div className={styles.timelineItem} key={event}><strong>{event}</strong><small>{date}</small></div>)}</div>
        </Panel>

        <Panel className={styles.profileWide}>
          <SectionTitle title="Мои сертификаты" action={<button className={styles.linkButton} type="button">Смотреть все</button>} />
          <div className={styles.certificateGrid}>{[["Стратегическое мышление", "Halyk Academy · Фев 2025"], ["Управление проектами", "Coursera · Ноя 2024"], ["Аналитика данных для бизнеса", "Halyk Academy · Сен 2024"]].map(([title, meta]) => <article className={styles.certificate} key={title}><span className={styles.iconTile}>CERT</span><div><strong>{title}</strong><small>{meta}</small></div></article>)}</div>
        </Panel>

        <Panel>
          <SectionTitle title="Настройки видимости" action={<button className={styles.linkButton} type="button" onClick={() => setNotice("Настройки видимости сохранены")}>Сохранить</button>} />
          <div className={styles.visibilityRow}><div><strong>Видимость профиля</strong><small>Кто может видеть ваш профиль</small></div><select className={styles.select} value={profileVisibility} onChange={(event) => setProfileVisibility(event.target.value)} aria-label="Видимость профиля"><option value="team">Для всех в компании</option><option value="department">Только мой департамент</option><option value="private">Только я</option></select></div>
          <div className={styles.visibilityRow}><div><strong>Видимые разделы</strong><small>Какие данные показывать другим</small></div><select className={styles.select} value={sectionsVisibility} onChange={(event) => setSectionsVisibility(event.target.value)} aria-label="Видимые разделы"><option value="skills">Навыки, достижения, портфолио</option><option value="portfolio">Только портфолио</option><option value="none">Не показывать разделы</option></select></div>
        </Panel>
      </div>

      {editOpen && <div className={styles.dialogBackdrop} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditOpen(false); }}><div className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="profile-dialog-title"><h2 id="profile-dialog-title">Редактировать профиль</h2><p>Можно изменить только публичные контактные данные. Роль и подразделение синхронизируются с HR-системой.</p><label htmlFor="profile-name">Имя</label><input id="profile-name" className={styles.search} value={draftName} onChange={(event) => setDraftName(event.target.value)} /><label htmlFor="profile-city" style={{ display: "block", marginTop: 12 }}>Город</label><input id="profile-city" className={styles.search} value={draftCity} onChange={(event) => setDraftCity(event.target.value)} /><div className={styles.dialogActions}><button className={styles.ghostButton} type="button" onClick={() => setEditOpen(false)}>Отмена</button><button className={styles.primaryButton} type="button" onClick={saveProfile}>Сохранить</button></div></div></div>}
    </main>
  );
}
