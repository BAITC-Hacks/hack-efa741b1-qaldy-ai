"use client";

import Link from "next/link";
import { type CSSProperties, type ReactNode, useMemo, useState } from "react";

const quests = [
  { title: "Клиентский кейс", type: "Командный квест", skill: "Клиентоориентированность", progress: 40, xp: 200, status: "Активный", due: "10 мая 2026" },
  { title: "Лидерство в действии", type: "Индивидуальный", skill: "Лидерство", progress: 25, xp: 150, status: "Активный", due: "30 апр. 2026" },
  { title: "Инновационное решение", type: "Индивидуальный", skill: "Критическое мышление", progress: 0, xp: 250, status: "Доступный", due: "15 окт. 2026" },
  { title: "Запросить обратную связь", type: "Индивидуальный", skill: "Коммуникация", progress: 0, xp: 100, status: "Доступный", due: "20 окт. 2026" },
];

function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`cq-panel ${className}`}>{children}</section>;
}

function IconTile({ children, tone = "green" }: { children: ReactNode; tone?: string }) {
  return <span aria-hidden="true" className={`icon-tile ${tone}`}>{children}</span>;
}

function Progress({ value, label }: { value: number; label?: string }) {
  return (
    <div aria-label={label ?? `Прогресс ${value}%`} aria-valuemax={100} aria-valuemin={0} aria-valuenow={value} className="cq-progress" role="progressbar">
      <i style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

function Ring({ value, small = false }: { value: number; small?: boolean }) {
  return <span aria-label={`Готовность ${value}%`} aria-valuemax={100} aria-valuemin={0} aria-valuenow={value} className={`progress-ring ${small ? "small" : ""}`} role="progressbar" style={{ "--value": `${value * 3.6}deg` } as CSSProperties}><b>{value}%</b></span>;
}

function SectionHeading({ title, action, href }: { title: string; action?: string; href?: string }) {
  return (
    <div className="section-title"><h2>{title}</h2>{action && (href ? <Link href={href}>{action} <span>→</span></Link> : <button type="button">{action} <span>→</span></button>)}</div>
  );
}

function PageTitle({ title, subtitle, goal = true }: { title: string; subtitle: string; goal?: boolean }) {
  return (
    <div className="prototype-heading">
      <div><h1>{title}</h1><p>{subtitle}</p></div>
      {goal && <Panel className="goal-strip"><IconTile>◎</IconTile><span><small>Ваша цель:</small><strong>Руководитель проекта</strong></span><Ring value={72} /><small>Готовность</small></Panel>}
    </div>
  );
}

function QuestMiniCard({ item }: { item: (typeof quests)[number] }) {
  return (
    <article className="quest-mini-card">
      <div className="card-meta"><span className={item.status === "Активный" ? "status green" : "status blue"}>{item.status}</span><button aria-label={`Меню квеста ${item.title}`} type="button">•••</button></div>
      <h3>{item.title}</h3><p>{item.type}</p>
      <div className="tag-row"><span>{item.skill}</span></div>
      <div className="progress-with-label"><Progress value={item.progress} /><b>{item.progress}%</b></div>
      <div className="quest-facts"><span>Срок: {item.due}</span><strong>XP +{item.xp}</strong></div>
      <button className="button secondary wide" type="button">{item.progress ? "Продолжить" : "Начать"} →</button>
    </article>
  );
}

export function HomeScreen() {
  const [taskProgress, setTaskProgress] = useState(2);
  return (
    <main className="prototype-page" id="main-content">
      <PageTitle title="Доброе утро, Анна!" subtitle="Ваш следующий шаг уже готов" />
      <div className="home-top-grid">
        <Panel className="today-panel">
          <SectionHeading title="Сегодня" />
          <article className="featured-task">
            <IconTile>▤</IconTile><div><h3>Завершить кейс по фасилитации</h3><p>Развивайте навык «Коммуникация»</p><div className="progress-with-label"><Progress value={taskProgress * 30} /><b>{taskProgress}/3</b></div></div>
            <button className="button primary" onClick={() => setTaskProgress((value) => Math.min(3, value + 1))} type="button">{taskProgress === 3 ? "Готово" : "Продолжить"} →</button>
          </article>
          <Link className="task-row" href="/learning"><IconTile>▶</IconTile><span><strong>Пройти урок «Управление стейкхолдерами»</strong><small>Обучение · 15 мин</small></span><b>›</b></Link>
          <Link className="task-row" href="/team"><IconTile>•••</IconTile><span><strong>Получить обратную связь от руководителя</strong><small>Развитие · 1 задача</small></span><b>›</b></Link>
        </Panel>
        <div className="home-side-stack">
          <div className="two-card-row">
            <Panel className="next-step"><SectionHeading title="Следующий шаг" /><strong>+6% <small>к готовности</small></strong><p>Завершите текущий кейс и приблизьтесь к цели</p><b>XP +120 XP</b></Panel>
            <Panel className="ai-tip"><SectionHeading title="AI-рекомендация" /><div><IconTile tone="yellow">★</IconTile><strong>Сфокусируйтесь<br />на навыке «Лидерство»</strong></div><p>Этот навык повысит ваши возможности для роста.</p><Link className="button secondary wide" href="/ai-navigator">Показать рекомендации →</Link></Panel>
          </div>
          <Panel><SectionHeading title="Мой карьерный маршрут" /><div className="compact-route"><span className="done">✓<small>Аналитик</small></span><i /><span className="done">✓<small>Старший аналитик</small></span><i /><span className="current">●<small>Руководитель проекта</small></span></div></Panel>
        </div>
      </div>
      <div className="dashboard-grid">
        <Panel className="span-2"><SectionHeading action="Смотреть все" href="/quests" title="Активные квесты" /><div className="mini-quest-grid">{quests.slice(0, 3).map((item) => <QuestMiniCard item={item} key={item.title} />)}</div></Panel>
        <Panel><SectionHeading action="Смотреть все" href="/learning" title="Обучение" /><div className="learning-compact"><div className="media-placeholder">▶</div><div><strong>Стратегическое мышление</strong><p>Онлайн-курс · 2 часа</p><Progress value={60} /></div></div><Link className="button secondary wide" href="/learning">Продолжить обучение →</Link></Panel>
        <Panel><SectionHeading action="Смотреть все" href="/opportunities" title="Возможности для вас" /><Link className="opportunity-line" href="/opportunities"><IconTile>●●</IconTile><span><strong>Ротация в PMO · совпадение 86%</strong><small>Новая возможность внутри компании</small></span><b>›</b></Link><div className="tag-row"><span>Развитие</span><span>Ротация</span><span>PMO</span></div></Panel>
        <Panel><SectionHeading title="Командная миссия" /><div className="mission-line"><IconTile>●●</IconTile><span><strong>Клиентский кейс · 3/5</strong><small>Совместное решение для реального клиента</small></span></div><div className="progress-with-label"><Progress value={60} /><b>60%</b></div><Link className="button secondary" href="/team">Перейти к миссии →</Link></Panel>
        <Panel><SectionHeading action="Смотреть все" href="/profile" title="Мои достижения" /><div className="achievement-row"><span><b>★ 5</b><small>Завершённых<br />квестов</small></span><span><b>◆ 4</b><small>Серия<br />недель</small></span><span><b>▥ 1 250</b><small>Всего XP</small></span></div></Panel>
      </div>
    </main>
  );
}

export function CareerMapScreen() {
  const [evidence, setEvidence] = useState([true, true, false]);
  const complete = evidence.filter(Boolean).length;
  return (
    <main className="prototype-page" id="main-content">
      <PageTitle title="Моя карьерная карта" subtitle="Исследуйте возможности. Развивайте навыки. Создавайте своё будущее." />
      <div className="content-with-aside">
        <div className="content-stack">
          <Panel className="career-path-panel">
            <div className="career-path">
              <div className="path-node done"><b>✓</b><strong>Аналитик</strong></div><i />
              <div className="path-node done"><b>✓</b><strong>Старший<br />аналитик</strong><small>Пройдено</small></div><i />
              <div className="path-node current"><b>●</b><strong>Руководитель<br />проекта</strong><small>Целевая роль</small></div><i className="dashed" />
              <div className="branch"><div className="path-node locked"><b>▥</b><strong>Data Lead</strong></div><div className="path-node locked"><b>▣</b><strong>Product Manager</strong></div></div>
            </div>
          </Panel>
          <Panel className="main-quest-panel">
            <div className="quest-main-copy"><span className="eyebrow-green">★ ГЛАВНЫЙ КВЕСТ</span><h2>Провести презентацию проекта</h2><p>Подготовьте и проведите презентацию для ключевых стейкхолдеров.</p><div className="progress-with-label"><Progress value={60} /><b>60%</b></div><div className="reward-row"><b>XP +120 XP</b><span>Коммуникация +1</span><span>Срок: 24 окт. 2026</span></div></div>
            <div className="evidence-list"><div><strong>Подтверждающие материалы</strong><span>{complete}/3</span></div>{["Черновик презентации", "Провести презентацию", "Получить обратную связь"].map((label, index) => <label key={label}><input checked={evidence[index]} onChange={() => setEvidence((items) => items.map((value, itemIndex) => itemIndex === index ? !value : value))} type="checkbox" /><span>{label}</span></label>)}<button className="button primary wide" type="button">Продолжить →</button></div>
          </Panel>
          <div className="three-columns"><Panel><SectionHeading action="Смотреть все" href="/quests" title="Активные квесты" /><QuestMiniCard item={quests[0]} /></Panel><Panel><SectionHeading action="Смотреть все" href="/profile" title="Последние достижения" /><div className="badge-grid"><span>★<small>Первый проект</small></span><span>●<small>Наставник</small></span><span>▣<small>30 дней развития</small></span></div></Panel><Panel><SectionHeading action="Смотреть все" href="/opportunities" title="Возможности для вас" /><div className="opportunity-line"><IconTile>●●</IconTile><span><strong>Открыто: ротация в PMO</strong><small>Новая возможность внутри компании</small></span></div></Panel></div>
        </div>
        <aside className="right-rail"><Panel className="ai-tip"><SectionHeading title="AI-навигатор" /><p><strong>Завершите кейс по фасилитации</strong> — готовность вырастет до 78%</p><Link className="button secondary wide" href="/ai-navigator">Показать рекомендации →</Link></Panel><Panel><SectionHeading title="Дерево навыков" />{[["Аналитика",80,"4/5"],["Коммуникация",60,"3/5"],["Лидерство",40,"2/5"]].map(([label,value,note]) => <div className="skill-line" key={String(label)}><div><strong>{label}</strong><span>{note}</span></div><Progress value={Number(value)} /></div>)}<Link className="button secondary wide" href="/skills">Открыть все навыки →</Link></Panel><blockquote>Сегодняшние усилия — завтрашние возможности.</blockquote></aside>
      </div>
    </main>
  );
}

export function QuestsScreen() {
  const [tab, setTab] = useState("Активные");
  const [query, setQuery] = useState("");
  const [evidence, setEvidence] = useState([true, true, false]);
  const filtered = useMemo(() => quests.filter((item) => (tab === "Все" || item.status === tab.slice(0, -1)) && item.title.toLowerCase().includes(query.toLowerCase())), [query, tab]);
  return (
    <main className="prototype-page" id="main-content">
      <PageTitle goal={false} title="Квесты" subtitle="Превращайте развитие в измеримый прогресс" />
      <div className="stat-strip">{[["Активные","4","Вы выполняете сейчас"],["Доступные","12","Новые возможности"],["Завершённые","18","Ваши достижения"]].map(([label,value,desc]) => <Panel key={label}><IconTile>{value}</IconTile><span><strong>{label}</strong><small>{desc}</small></span><b>{value}</b></Panel>)}</div>
      <Panel className="quest-hero"><div className="quest-visual">▥</div><div className="quest-main-copy"><span className="status green">Главный квест</span><h2>Провести презентацию проекта</h2><p>Покажите результаты проекта команде и стейкхолдерам</p><div className="progress-with-label"><Progress value={60} /><b>60%</b></div><div className="reward-row"><span>Срок 24 окт. 2026</span><span>Средняя сложность</span><b>XP +120</b><span>Коммуникация +1</span></div></div><div className="evidence-list"><div><strong>Доказательства</strong><span>{evidence.filter(Boolean).length}/3</span></div>{["Черновик презентации","Провести презентацию","Получить обратную связь"].map((label,index) => <label key={label}><input checked={evidence[index]} onChange={() => setEvidence((items) => items.map((value,itemIndex) => itemIndex === index ? !value : value))} type="checkbox" /><span>{label}</span></label>)}<button className="button primary wide" type="button">Продолжить →</button></div></Panel>
      <Panel className="quest-catalog">
        <div className="catalog-toolbar"><div className="tabs" role="tablist">{["Активные","Доступные","Завершённые","Все"].map((label) => <button aria-selected={tab === label} className={tab === label ? "active" : ""} key={label} onClick={() => setTab(label)} role="tab" type="button">{label}</button>)}</div><input aria-label="Поиск квестов" onChange={(event) => setQuery(event.target.value)} placeholder="Поиск квестов..." type="search" value={query} /></div>
        {filtered.length ? <div className="quest-grid">{filtered.map((item) => <QuestMiniCard item={item} key={item.title} />)}</div> : <div className="empty-state"><strong>Квесты не найдены</strong><p>Измените запрос или выберите другую вкладку.</p><button className="button secondary" onClick={() => { setQuery(""); setTab("Все"); }} type="button">Сбросить фильтры</button></div>}
      </Panel>
    </main>
  );
}

export function SkillsScreen() {
  const skills = [["Аналитика",4,5],["Коммуникация",3,5],["Лидерство",2,5],["Управление проектами",3,5],["Стратегическое мышление",2,5]] as const;
  return (
    <main className="prototype-page" id="main-content">
      <PageTitle title="Мои навыки" subtitle="Подтверждённые компетенции и зоны роста" />
      <div className="content-with-aside skills-layout">
        <div className="content-stack">
          <Panel><SectionHeading title="Карта профессиональных навыков" /><div className="skill-map">{skills.map(([name,value],index) => <div className={`skill-node ${value >= 3 ? "mastered" : "growing"}`} key={name}><b>{index % 2 ? "●●" : "▥"}</b><strong>{name}</strong><span>{value >= 3 ? "✓" : "○"}</span><small>{value >= 3 ? "Освоен" : "В развитии"}</small></div>)}</div></Panel>
          <Panel><SectionHeading action="Смотреть все" title="Мои ключевые компетенции" /><div className="competency-grid">{skills.map(([name,value,total]) => <article key={name}><IconTile>{value}</IconTile><strong>{name}</strong><div className="progress-with-label"><Progress value={value / total * 100} /><b>{value}/{total}</b></div><p>{value >= 4 ? "Уверенное владение" : "Зона развития"}</p></article>)}</div></Panel>
          <Panel><SectionHeading action="Смотреть все" title="Разрыв до целевой роли" /><div className="gap-cards">{[["Лидерство",40],["Стратегическое мышление",50],["Управление изменениями",30]].map(([name,value]) => <article key={String(name)}><strong>{name}</strong><div className="progress-with-label"><Progress value={Number(value)} /><b>{value}%</b></div><small>Текущий уровень 2/5 · Нужно 4/5</small></article>)}</div></Panel>
        </div>
        <aside className="right-rail"><Panel className="ai-tip"><SectionHeading title="Что развивать дальше" /><h3>Рекомендуем сфокусироваться на навыке «Лидерство»</h3><p>Ключевой навык для достижения целевой роли. Повысит готовность примерно на 15%.</p><Link className="button primary wide" href="/ai-navigator">Получить план →</Link></Panel><Panel><SectionHeading title="Баланс компетенций" /><svg aria-label="Диаграмма текущих и требуемых навыков" className="radar-chart" role="img" viewBox="0 0 240 210"><polygon points="120,15 216,84 180,195 60,195 24,84" /><polygon className="target" points="120,43 190,94 164,174 76,174 50,94" /><polygon className="actual" points="120,62 168,100 150,151 82,160 64,100" /><circle cx="120" cy="62" r="4" /><circle cx="168" cy="100" r="4" /><circle cx="150" cy="151" r="4" /><circle cx="82" cy="160" r="4" /><circle cx="64" cy="100" r="4" /></svg><ul className="sr-only"><li>Аналитика: 4 из 5</li><li>Коммуникация: 3 из 5</li><li>Лидерство: 2 из 5</li></ul></Panel><Panel><SectionHeading title="Подтверждение навыков" /><div className="proof-grid"><span>▤<small>Сертификат<br />5 навыков</small></span><span>▣<small>Артефакт<br />3 навыка</small></span><span>•••<small>Обратная связь<br />4 навыка</small></span></div></Panel></aside>
      </div>
    </main>
  );
}

export function AiNavigatorScreen() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  function send(text: string) {
    if (!text.trim() || loading) return;
    setMessages((items) => [...items, text.trim()]);
    setMessage(""); setLoading(true);
    window.setTimeout(() => setLoading(false), 550);
  }
  return (
    <main className="prototype-page" id="main-content">
      <PageTitle title="AI-навигатор" subtitle="Понимайте, зачем нужен каждый следующий шаг" />
      <div className="ai-layout">
        <Panel className="chat-panel">
          <div className="chat-message user"><span className="avatar-photo">АС</span><p>Что мне сделать, чтобы стать руководителем проекта?</p></div>
          <div className="chat-message assistant"><IconTile>AI</IconTile><div><h3>Отличный вопрос, Анна!</h3><p>Чтобы стать руководителем проекта в Halyk, предлагаю пройти три ключевых шага. Они основаны на требованиях к роли, вашем уровне навыков и успешных карьерных траекториях.</p><div className="development-plan"><h3>Ваш план развития</h3>{[["Завершить кейс по фасилитации","Коммуникация","+8%"],["Провести командную презентацию","Лидерство","+7%"],["Пройти оценку лидерства","Стратегическое мышление","+5%"]].map(([title,skill,impact],index) => <div className="plan-step" key={title}><b>{index + 1}</b><IconTile>{index + 1}</IconTile><span><strong>{title}</strong><small>{skill} · ~{index + 2} недели</small></span><em>{impact}</em><button className={index ? "button secondary" : "button primary"} type="button">{index ? "Запланировать" : "Продолжить"} →</button></div>)}</div><div className="response-actions"><button aria-label="Ответ полезен" type="button">♡</button><button aria-label="Ответ не полезен" type="button">⊘</button></div></div></div>
          {messages.map((item) => <div className="chat-message user" key={item}><span className="avatar-photo">АС</span><p>{item}</p></div>)}
          {loading && <div aria-live="polite" className="chat-message assistant"><IconTile>AI</IconTile><p className="typing">Анализирую карьерную траекторию<span>...</span></p></div>}
          <div className="quick-prompts">{["Изменить карьерную цель","Объяснить рекомендацию","Составить план на месяц","Найти ротацию"].map((label) => <button onClick={() => send(label)} type="button" key={label}>{label}</button>)}</div>
          <form className="chat-input" onSubmit={(event) => { event.preventDefault(); send(message); }}><button aria-label="Прикрепить файл" type="button">＋</button><input aria-label="Сообщение AI-навигатору" onChange={(event) => setMessage(event.target.value)} placeholder="Спросите о своём развитии..." value={message} /><button aria-label="Отправить сообщение" disabled={!message.trim() || loading} type="submit">➤</button></form>
        </Panel>
        <aside className="right-rail"><Panel><SectionHeading title="Влияние на цель" /><div className="impact-rings"><span><small>Текущая</small><Ring value={72} /></span><b>→</b><span><small>После плана</small><Ring value={84} /></span><strong>+12%<small>готовности</small></strong></div></Panel><Panel><SectionHeading title="Почему эти шаги" /><ul className="check-list"><li>Требования к роли «Руководитель проекта»</li><li>Ваш текущий уровень навыков</li><li>Успешные траектории коллег</li></ul><button className="text-action" type="button">Подробнее о методологии →</button></Panel><Panel><SectionHeading title="Источники данных" /><div className="source-grid"><span>Ваш профиль<small>Навыки и опыт</small></span><span>Обратная связь<small>От руководителя</small></span><span>Пройденные курсы<small>Результаты обучения</small></span><span>Ролевая модель<small>Успешные кейсы</small></span></div></Panel><Panel><SectionHeading title="Альтернативный маршрут" /><Link className="opportunity-line" href="/career-map"><IconTile>⇄</IconTile><span><strong>Сначала стать старшим аналитиком</strong><small>Усилить экспертизу, затем перейти к управлению проектами.</small></span></Link></Panel></aside>
      </div>
    </main>
  );
}
