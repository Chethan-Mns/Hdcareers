#!/usr/bin/env python3
"""Strict, fail-closed public-source gate before the daily owner review.

Does not publish or expire anything. Non-Live candidates remain in
verificationHold for later source inspection, not in Priority/Backup.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_job_availability import check, has_high_confidence_live


def preflight(batch, checker=check, now=None, workers=5):
    now = now or datetime.now(timezone.utc)
    original = list(batch.get('priority') or []) + list(batch.get('backup') or [])
    if batch.get('status') in ('submitted', 'published') or any(
        x.get('reviewedAt') or x.get('reviewedStatus', 'unreviewed') not in ('', 'unreviewed')
        for x in original
    ):
        return batch, {'skipped': True, 'reason': 'Never revise submitted or owner-reviewed batches',
                       'items': []}
    if not original:
        return batch, {'skipped': True, 'reason': 'No candidates to verify', 'items': []}

    def verify(item):
        job = item.get('job') or {}
        url = str(job.get('apply') or '')
        if not url.startswith('https://') or str(item.get('apply') or '') != url:
            return item, {'state': 'review', 'reason': 'Candidate and exact official HTTPS apply URL do not match',
                          'checkedAt': now.isoformat()}
        try:
            return item, checker(job, now=now)
        except Exception as exc:
            return item, {'state': 'review', 'reason': 'Verifier failed (' + type(exc).__name__ + ')',
                          'checkedAt': now.isoformat()}

    verified = {}
    with ThreadPoolExecutor(max_workers=max(1, min(8, workers))) as pool:
        futures = [pool.submit(verify, x) for x in original]
        for future in as_completed(futures):
            candidate, result = future.result()
            verified[str(candidate['id'])] = result

    accepted, held, details = [], [], []
    for candidate in original:
        result = verified[str(candidate['id'])]
        good = has_high_confidence_live(candidate.get('job') or {}, result)
        evidence = {'checkedAt': now.isoformat(), 'decision': 'verified_live' if good else 'held_for_review',
                    'observedState': result.get('state', 'review'), 'reason': result.get('reason', '')}
        next_candidate = dict(candidate)
        next_candidate['liveSourceEvidence'] = evidence
        next_candidate['verificationVerdict'] = 'live' if good else 'unconfirmed'
        if good:
            accepted.append(next_candidate)
        else:
            held.append(next_candidate)
        details.append({'id': candidate['id'], 'company': candidate.get('company') or
                        candidate.get('job', {}).get('company'), 'officialUrl': candidate.get('apply'),
                        **evidence})

    # Preserve ranking order; never manufacture quota-fillers or mark jobs expired.
    result = {**batch, 'priority': accepted[:10], 'backup': accepted[10:20],
              'verificationHold': held, 'verifiedLiveCount': len(accepted),
              'verificationCheckedAt': now.isoformat(),
              'verificationPolicy': 'exact live evidence only; unverified postings hidden from daily active review'}
    report = {'batchId': batch.get('batchId'), 'checkedAt': now.isoformat(),
              'checked': len(original), 'verifiedLive': len(accepted),
              'heldForReview': len(held), 'shortfall': max(0, 20-len(accepted)),
              'items': details, 'applied': False,
              'policy': 'No job is automatically marked expired or published by this scan.'}
    return result, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('batch', nargs='?', default='data/daily-review-batch.json')
    parser.add_argument('--apply', action='store_true', help='Hide non-confirmed candidates in verificationHold')
    parser.add_argument('--report', default='')
    args = parser.parse_args()
    p = Path(args.batch)
    updated, report = preflight(json.loads(p.read_text(encoding='utf-8')))
    report['applied'] = bool(args.apply and not report.get('skipped'))
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    if report['applied']:
        p.write_text(json.dumps(updated, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(f"High-confidence Live: {report.get('verifiedLive',0)}/{report.get('checked',0)}; "
          f"held {report.get('heldForReview',0)} uncertain jobs; no publication attempted.")
    if not report.get('skipped') and not report.get('verifiedLive'):
        print('WARNING: no high-confidence candidate; daily shortlist left empty rather than falsely marked Live.')


if __name__ == '__main__':
    main()
