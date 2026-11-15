import { useEffect, useState } from 'react'
import { requestJson } from './shared/api/client'

type Status = 'loading' | 'ready' | 'error'

export default function App() {
  const [status, setStatus] = useState<Status>('loading')
  useEffect(() => {
    const controller = new AbortController()
    requestJson<{ status: string; service: string }>('health', controller.signal)
      .then((data) => {
        if (data.status !== 'ok' || data.service !== 'masterly-api') throw new Error('Invalid health response')
        setStatus('ready')
      })
      .catch(() => { if (!controller.signal.aborted) setStatus('error') })
    return () => controller.abort()
  }, [])

  return (
    <main>
      <p className="eyebrow">Платформа онлайн-записи</p>
      <h1>MASTERLY</h1>
      <p>Основа проекта подготовлена. Каталог и бронирование находятся в разработке.</p>
      <section aria-labelledby="status-title">
        <h2 id="status-title">Подключение API</h2>
        <p role="status">
          {status === 'loading' && 'Проверяем подключение…'}
          {status === 'ready' && 'API доступен. Подключение базы данных пока не проверяется.'}
          {status === 'error' && 'API недоступен. Проверьте запуск сервера и адрес в конфигурации.'}
        </p>
      </section>
    </main>
  )
}
