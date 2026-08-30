import hashlib, pathlib, subprocess, json
REPO=pathlib.Path('/private/tmp/proposalops-ui-final-cert-repair'); E4='5f994931f3ddbe3a6266d6bdb6a8681956fc9e9e'; manifest='artifacts/ui-ux-r1-clean-handoff-v4/SHA256SUMS_PAYLOAD'; prefix='artifacts/ui-ux-r1-clean-handoff-v4/'
def show(p):
 target=p if p==manifest else prefix+p
 return subprocess.run(['git','show',f'{E4}:{target}'],cwd=REPO,stdout=subprocess.PIPE,check=True).stdout
rows=[]
for line in show(manifest).decode().splitlines():
 h,p=line.split('  ',1); rows.append((h,p))
missing=[]; mismatches=[]; duplicates=[]; seen=set(); absolute=[]
for expected,p in rows:
 if p in seen: duplicates.append(p)
 seen.add(p)
 if p.startswith('/') : absolute.append(p)
 try: actual=hashlib.sha256(show(p)).hexdigest()
 except subprocess.CalledProcessError: missing.append(p); continue
 if actual!=expected: mismatches.append({'path':p,'expected':expected,'observed':actual})
out={'MANIFEST_ROWS':len(rows),'MANIFEST_MISSING':len(missing),'MANIFEST_EXTRA_DUPLICATE_PATHS':len(duplicates),'MANIFEST_HASH_MISMATCHES':len(mismatches),'MANIFEST_ABSOLUTE_PATHS':len(absolute),'missing_paths':missing,'duplicate_paths':duplicates,'hash_mismatches':mismatches,'absolute_paths':absolute,'RESULT':'PASS' if not missing and not duplicates and not mismatches and not absolute else 'FAIL'}
pathlib.Path(__file__).parent.parent.joinpath('08-manifest-validation-final.json').write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out)); raise SystemExit(0 if out['RESULT']=='PASS' else 1)
