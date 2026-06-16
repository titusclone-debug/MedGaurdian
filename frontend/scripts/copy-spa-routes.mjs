import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'

const distDir = join(process.cwd(), 'dist')
const indexPath = join(distDir, 'index.html')

const routes = [
  'fcra',
  'dpdp',
  'bmw',
  'nabh',
  'licenses',
  'risk',
  'hq',
  'staff',
]

if (!existsSync(indexPath)) {
  throw new Error(`Cannot create SPA route fallbacks because ${indexPath} does not exist.`)
}

for (const route of routes) {
  const routeDir = join(distDir, route)
  mkdirSync(routeDir, { recursive: true })
  copyFileSync(indexPath, join(routeDir, 'index.html'))
}

console.log(`Created SPA route fallbacks for ${routes.length} routes.`)
