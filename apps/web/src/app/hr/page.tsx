const modules = [
  ["Дефициты навыков", "Частые и критичные разрывы по ролям и грейдам."],
  ["Участие", "Завершения, пропуски и отказы по активностям."],
  ["Нет следующего шага", "Сотрудники и причины отсутствия рекомендации."],
  ["Пробелы каталога", "Навыки, для которых нет доступной активности."],
];

export default function HrPage() {
  return (
    <main className="page-content">
      <div className="eyebrow">HR workspace</div>
      <div className="page-heading">
        <div>
          <h1>Командное развитие</h1>
          <p>Каркас модулей HR. Данные и фильтры подключаются на следующем этапе.</p>
        </div>
        <span className="status-pill muted">Структура MVP</span>
      </div>
      <section className="module-grid" aria-label="HR modules">
        {modules.map(([title, description]) => (
          <article className="module-card" key={title}>
            <span className="module-icon" aria-hidden="true" />
            <h2>{title}</h2>
            <p>{description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
