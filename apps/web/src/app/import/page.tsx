export default function ImportPage() {
  return (
    <main className="page-content">
      <div className="eyebrow">Data workspace</div>
      <div className="page-heading">
        <div>
          <h1>Импорт проверочных профилей</h1>
          <p>Здесь появится dry-run проверка JSON/CSV перед применением данных.</p>
        </div>
        <span className="status-pill muted">Следующий этап</span>
      </div>
      <section className="empty-panel">
        <span className="upload-mark">JSON / CSV</span>
        <h2>Валидация до загрузки</h2>
        <p>Файл, строка, поле и причина ошибки будут показаны до изменения хранилища.</p>
      </section>
    </main>
  );
}
