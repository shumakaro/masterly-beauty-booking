import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('does not claim that the database is ready when API liveness succeeds', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, json: async () => ({ status: 'ok', service: 'masterly-api' }),
  }))
  render(<App />)
  expect(await screen.findByText(/базы данных пока не проверяется/)).toBeInTheDocument()
})

it('shows an actionable error when the API is unavailable', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  render(<App />)
  expect(await screen.findByText(/API недоступен/)).toBeInTheDocument()
})
