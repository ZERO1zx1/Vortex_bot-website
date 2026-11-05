/**
 * Structural check for the generated command catalog.
 *
 * Reads src/data/commands.js as an ES module and asserts the shape the UI
 * depends on. Exits non-zero when a command would break rendering.
 *
 *   node website/tools/validate_commands.mjs
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(
  join(here, '..', 'src', 'data', 'commands.js'),
  'utf8'
)

// The file has no imports, so a data: URL module is enough to evaluate it.
const module = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
)
const { COMMAND_LIST, COMMAND_CATS, CAT_META } = module

const counts = COMMAND_LIST.reduce((acc, c) => {
  acc[c.type] = (acc[c.type] || 0) + 1
  return acc
}, {})

const VALID_TYPES = ['slash', 'text']
const problems = []
const seen = new Set()

for (const c of COMMAND_LIST) {
  const where = `command "${c.name}"`
  if (!c.name) problems.push(`${where}: missing name`)
  if (seen.has(c.name)) problems.push(`${where}: duplicate name`)
  seen.add(c.name)
  if (!VALID_TYPES.includes(c.type))
    problems.push(`${where}: invalid type "${c.type}"`)
  if (!c.cat) problems.push(`${where}: missing cat`)
  else if (!CAT_META[c.cat])
    problems.push(`${where}: cat "${c.cat}" has no CAT_META entry`)
  if (!c.desc) problems.push(`${where}: missing Mongolian desc`)
  if (!c.descEN) problems.push(`${where}: missing English descEN`)
  if (typeof c.example !== 'string' || !c.example.trim())
    problems.push(`${where}: missing example`)
  if (!Array.isArray(c.args)) problems.push(`${where}: args must be an array`)
}

for (const cat of COMMAND_CATS) {
  if (!CAT_META[cat])
    problems.push(`COMMAND_CATS: "${cat}" has no CAT_META entry`)
}

console.log(
  JSON.stringify({ total: COMMAND_LIST.length, counts, problems }, null, 2)
)
if (problems.length) process.exit(1)
