import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('repair_schema_drift only creates missing ORM tables instead of re-creating indexes on existing tables', () => {
  const source = readFileSync('deployment/scripts/repair_schema_drift.py', 'utf8')

  assert.match(source, /from sqlalchemy import create_engine, inspect/)
  assert.match(source, /from sqlalchemy\.exc import ProgrammingError/)
  assert.match(source, /def ensure_hotspot_tables\(cursor\) -> None:/)
  assert.match(source, /def ensure_articles_schema\(cursor\) -> None:/)
  assert.match(source, /CREATE TABLE IF NOT EXISTS hotspot_sources/)
  assert.match(source, /CREATE TABLE IF NOT EXISTS hotspot_items/)
  assert.match(source, /CREATE TABLE IF NOT EXISTS hotspot_rank_history/)
  assert.match(source, /ALTER TABLE articles ADD COLUMN IF NOT EXISTS username VARCHAR\(100\)/)
  assert.match(source, /CREATE INDEX IF NOT EXISTS idx_articles_username ON articles\(username\)/)
  assert.match(source, /managed_by_sql = \{"hotspot_sources", "hotspot_items", "hotspot_rank_history"\}/)
  assert.match(source, /inspector = inspect\(engine\)/)
  assert.match(source, /if inspector\.has_table\(table\.name\):/)
  assert.match(source, /table\.create\(bind=engine, checkfirst=True\)/)
  assert.match(source, /except ProgrammingError as exc:/)
  assert.match(source, /if "already exists" in str\(exc\)\.lower\(\):/)
  assert.doesNotMatch(source, /Base\.metadata\.create_all\(bind=engine, checkfirst=True\)/)
})
