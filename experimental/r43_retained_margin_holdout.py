#!/usr/bin/env python3
"""R43 predeclared, non-certifying, chronological MORE-EU retained-data triage pilot.

Fixed q=0.05, EXACTLY 3 contiguous days removed, fixed 14-array panel.
Input is source-pinned MORE-EU raw CSV, but outputs only derived aggregates.
Historical full-month values are used ONLY to evaluate deletion labels, never
as inputs to the test-time risk score. NOT a prospective field-outage study.
"""
import argparse, json, math
from pathlib import Path
import numpy as np
from r42_moreeu_original_source_analysis import input_months, qs_flag

GIT_BLOB = '5611277efdd581bb839ec380239846a43ebe0ba7'
Q = 0.05
L = 3
TRAIN_MONTHS = 55
REVIEW_BUDGET = 0.25

def auc(scores, labels):
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=bool)
    pos = scores[labels]; neg = scores[~labels]
    if not len(pos) or not len(neg):
        return None
    return float(((pos[:, None] > neg[None, :]).sum() +
                  0.5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))

def build(source):
    months, ncalendar, nrows = input_months(Path(source))
    assert len(months) == 79 and nrows == 280512
    observations = []
    for z in months:
        mask = (z['lengths'] == L)
        retained = z['keep'][mask]
        orig = qs_flag(z['full'], Q)
        wrong = np.any(qs_flag(retained, Q) != orig[None, :], axis=1)
        r = retained / retained.max(axis=1, keepdims=True)
        # 0 is most ambiguous; larger negative score means farther from shortlist edge.
        gap_to_boundary = np.min(np.abs(r-(1-Q)), axis=1)
        score = -gap_to_boundary
        for start, observed_score, label in zip(z['starts'][mask], score, wrong):
            observations.append({'month':z['month'], 'days':z['days'],
                                 'start':int(start), 'score':float(observed_score),
                                 'changed':bool(label), 'missing_pct':100*L/z['days']})
    assert len(observations)==2237 and sum(z['changed'] for z in observations)==430
    assert len({z['month'] for z in observations}) == 79
    train_months = [z['month'] for z in months[:TRAIN_MONTHS]]
    test_months = [z['month'] for z in months[TRAIN_MONTHS:]]
    train=[z for z in observations if z['month'] in set(train_months)]
    test=[z for z in observations if z['month'] in set(test_months)]
    assert set(z['month'] for z in train).isdisjoint(set(z['month'] for z in test))
    threshold=float(np.quantile([z['score'] for z in train],1-REVIEW_BUDGET))

    def summary(rows, split):
        y=np.array([x['changed'] for x in rows],bool)
        s=np.array([x['score'] for x in rows],float)
        rate=np.array([x['missing_pct'] for x in rows],float)
        flag = (s>=threshold)
        tp=int(np.sum(flag & y)); fp=int(np.sum(flag & ~y)); fn=int(np.sum(~flag & y)); tn=int(np.sum(~flag & ~y))
        bymonth=[]
        for m in sorted(set(x['month'] for x in rows)):
            rr=[x for x in rows if x['month']==m]
            yy=np.array([x['changed'] for x in rr],bool)
            ss=np.array([x['score'] for x in rr],float)
            bymonth.append({'month':m,'windows':len(rr),'changed':int(yy.sum()),
                            'within_month_auc':auc(ss,yy),
                            'flagged':int(np.sum(ss>=threshold)),
                            'changes_flagged':int(np.sum((ss>=threshold)&yy))})
        valid=[m['within_month_auc'] for m in bymonth if m['within_month_auc'] is not None]
        return {'split':split,'months':len(bymonth),'windows':len(rows),'changes':int(y.sum()),
                'changed_share':float(np.mean(y)), 'boundary_risk_auc':auc(s,y),
                'rate_only_auc_global':auc(rate,y),
                'n_mixed_months':len(valid),
                'median_within_month_auc':float(np.median(valid)) if valid else None,
                'months_with_auc_gt_half':sum(x>.5 for x in valid),
                'months_with_auc_lt_half':sum(x<.5 for x in valid),
                'flagged':int(flag.sum()),'flagged_share':float(flag.mean()),
                'tp':tp,'fp':fp,'fn':fn,'tn':tn,
                'recall_of_wrong_observed_only':tp/int(y.sum()) if int(y.sum()) else None,
                'precision_flagged':tp/int(flag.sum()) if int(flag.sum()) else None,
                'retained_wrong_after_review_flag':fn,
                'month_summary':bymonth}

    tr=summary(train,'earliest_55_months_train')
    te=summary(test,'latest_24_months_out_of_time')
    result={
        'experiment':'R43_OBSERVED_BOUNDARY_DISTANCE_TIME_HOLDOUT',
        'status':'EXPLORATORY_TEST_ONLY_NOT_CERTIFY',
        'source_git_blob':GIT_BLOB, 'source_raw_redistributed':False,
        'observed_score':'minus min_j abs(retained_yield_j/max_retained_yield - 0.95)',
        'q':Q,'exact_missing_days':L, 'fixed_candidates':14,
        'train_n_months':TRAIN_MONTHS,'test_n_months':79-TRAIN_MONTHS,
        'train_first_month':train_months[0],'train_last_month':train_months[-1],
        'test_first_month':test_months[0],'test_last_month':test_months[-1],
        'predefined_review_fraction':REVIEW_BUDGET,
        'training_only_score_threshold':threshold,
        'training':tr,'holdout':te,
        'claim_boundary':('Counterfactual deletion of originally complete months; wrong means '
           'retained-only shortlist differs from known complete-month shortlist; '
           'not observed fault/outage, not calibrated risk, not independent trials, '
           'not an error bound or operational correctness certificate.'),
        'scientific_gate':'AUTHOR_REVIEW_PENDING_MAIN_TEXT_UNCHANGED'
    }
    print('R43_HOLDOUT_SUMMARY',json.dumps({k:v for k,v in result.items() if k not in ('training','holdout')},sort_keys=True),flush=True)
    for a in (tr,te):
        print('R43_METRICS',json.dumps({k:v for k,v in a.items() if k!='month_summary'},sort_keys=True),flush=True)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True)
    parser.add_argument('--out',default='R43_DERIVED_ONLY')
    args=parser.parse_args()
    o=Path(args.out);o.mkdir(parents=True,exist_ok=True)
    result=build(args.source)
    (o/'R43_TIME_HOLDOUT_EVIDENCE.json').write_text(json.dumps(result,indent=2),encoding='utf8')
