import { expect, it, vi, afterEach } from 'vitest'
import { ApiError, requestJson } from './client'

afterEach(() => vi.unstubAllGlobals())

it('preserves HTTP error status for callers', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403 }))
  await expect(requestJson('health')).rejects.toEqual(new ApiError(403))
})
