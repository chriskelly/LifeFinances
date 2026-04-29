import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'

/** Required when Vitest `globals` is false — RTL only hooks global `afterEach`. */
afterEach(() => {
  cleanup()
})
