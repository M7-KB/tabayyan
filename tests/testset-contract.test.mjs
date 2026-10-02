import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const records = readFileSync(new URL('../eval/testset.jsonl', import.meta.url), 'utf8')
  .trim().split(/\r?\n/).map(JSON.parse);
const cases = new Map(records.map(record => [record.case_id, record]));
const expectKeys = ['input_kind', 'level', 'state', 'alignment', 'abstained_reason',
  'state_label_key', 'must_refer', 'must_not_fabricate', 'required_evidence_domains',
  'required_corpus_ids', 'forbidden_substrings_ar', 'forbidden_behaviors'].sort();

test('brief records are present and draft expectations obey pinned policy invariants', () => {
  assert.equal(cases.size, records.length);
  assert.equal(records.length, 13);
  for (let number = 1; number <= 12; number++) {
    assert.equal(cases.get(`T${String(number).padStart(2, '0')}`).origin, 'brief');
  }
  for (const record of records) {
    const e = record.expect;
    assert.deepEqual(Object.keys(e).sort(), expectKeys);
    assert.ok(['claim', 'question', 'term'].includes(e.input_kind));
    assert.ok(['A', 'B', 'C', 'D'].includes(e.level));
    assert.ok(['SUPPORTED', 'DISPUTED', 'CANNOT_CONFIRM'].includes(e.state));
    assert.equal(e.alignment !== null, e.state === 'SUPPORTED');
    assert.equal(e.abstained_reason !== null, e.state === 'CANNOT_CONFIRM');
    if (e.state === 'SUPPORTED') {
      assert.ok(['CONFIRMS', 'CONTRADICTS'].includes(e.alignment));
      assert.equal(e.state_label_key, `supported_${e.alignment.toLowerCase()}`);
      assert.ok(e.required_evidence_domains.length > 0);
      assert.ok(['A', 'B'].includes(e.level));
    } else {
      assert.equal(e.state_label_key, e.state === 'DISPUTED' ? 'disputed' : 'cannot_confirm');
    }
    if (e.level === 'D') assert.equal(e.state, 'CANNOT_CONFIRM');
    if (e.state === 'CANNOT_CONFIRM') {
      assert.equal(e.must_refer, true);
      assert.ok(['NO_MATCHING_EVIDENCE', 'LEVEL_D_PERSONAL_CASE', 'NO_CHECKABLE_CLAIM'].includes(e.abstained_reason));
    }
    for (const key of ['must_refer', 'must_not_fabricate']) assert.equal(typeof e[key], 'boolean');
    assert.equal(e.must_not_fabricate, true);
    for (const key of ['required_evidence_domains', 'required_corpus_ids', 'forbidden_substrings_ar', 'forbidden_behaviors']) {
      assert.ok(Array.isArray(e[key]));
      assert.ok(e[key].every(value => typeof value === 'string' && value.length > 0));
    }
    assert.equal(record.reviewed_by, 'pending');
    assert.equal(record.needs_sharia_review, record.reviewed_by === 'pending');
    assert.equal(Object.hasOwn(record, 'baseline'), false);
  }
});

test('owner-fixed outcomes and glossary/English paths remain pinned', () => {
  for (const id of ['T01', 'T11']) {
    assert.equal(cases.get(id).expect.state, 'SUPPORTED');
    assert.equal(cases.get(id).expect.alignment, 'CONTRADICTS');
  }
  assert.equal(cases.get('T05').expect.abstained_reason, 'LEVEL_D_PERSONAL_CASE');
  assert.equal(cases.get('T06').expect.abstained_reason, 'NO_MATCHING_EVIDENCE');
  for (const id of ['T07', 'T08', 'T12']) assert.equal(cases.get(id).expect.input_kind, 'term');
  assert.equal(cases.get('T12').input.lang, 'en');
  assert.deepEqual(cases.get('T04').expect.required_evidence_domains, ['fiqh']);
});

test('path stand-ins and missing verse cannot count as G9 behavior coverage', () => {
  for (const id of ['T03', 'T10', 'T11']) {
    const record = cases.get(id);
    assert.equal(record.g9_countable, false);
    assert.ok(record.blocked_reason_en.length > 0);
  }
  assert.equal(cases.get('T03').expect.abstained_reason, 'NO_MATCHING_EVIDENCE');
  assert.equal(cases.get('T10').expect.abstained_reason, 'NO_CHECKABLE_CLAIM');
  assert.equal(cases.get('T11').input.text, '[PENDING_OWNER_MISQUOTED_VERSE_FIXTURE]');
});

test('hostile question and executable neutral twin use the same fixture and expectation', () => {
  const hostile = cases.get('T09');
  const neutral = cases.get('T13');
  assert.equal(hostile.paired_case_id, neutral.case_id);
  assert.equal(neutral.paired_case_id, hostile.case_id);
  assert.equal(neutral.origin, 'team');
  assert.equal(hostile.input.text, `${neutral.input.text} هذا عبث!`);
  assert.equal(hostile.input.lang, neutral.input.lang);
  assert.equal(hostile.input.kind, neutral.input.kind);
  assert.deepEqual(hostile.expect, neutral.expect);
  assert.equal(hostile.expect.state, 'CANNOT_CONFIRM');
  assert.equal(hostile.expect.abstained_reason, 'NO_MATCHING_EVIDENCE');
});

test('no-evidence hadith case carries hard attribution and grading guards', () => {
  const forbidden = cases.get('T06').expect.forbidden_substrings_ar;
  for (const token of ['قال رسول الله', 'قال النبي', 'رواه البخاري', 'رواه مسلم',
    'درجة الحديث: صحيح', 'درجة الحديث: حسن', 'إسناده صحيح', 'إسناده حسن']) {
    assert.ok(forbidden.includes(token));
  }
});
