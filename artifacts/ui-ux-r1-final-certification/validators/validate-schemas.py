import json, pathlib, subprocess, jsonschema, importlib.metadata
REPO=pathlib.Path('/private/tmp/proposalops-ui-final-cert-repair'); E4='5f994931f3ddbe3a6266d6bdb6a8681956fc9e9e'; H4='3a7fe70ec447b4c977fc6cee60db5f8b149bbbab'
def show(c,p): return subprocess.run(['git','show',f'{c}:{p}'],cwd=REPO,stdout=subprocess.PIPE,check=True).stdout
def doc(c,p): return json.loads(show(c,p))
errors={}
for name,commit,schema_commit,docpath,schemapath in [('source',E4,E4,'artifacts/ui-ux-r1-clean-handoff-v4/13-final-source-result.json','artifacts/ui-ux-r1-clean-handoff-v4/schemas/final-source-result.schema.json'),('handoff',H4,E4,'artifacts/ui-ux-r1-clean-handoff-v4/24-azure-handoff.json','artifacts/ui-ux-r1-clean-handoff-v4/schemas/azure-handoff.schema.json')]:
 errors[name]=[e.message for e in jsonschema.Draft202012Validator(doc(schema_commit,schemapath)).iter_errors(doc(commit,docpath))]
out={'ENGINE':'python-jsonschema','ENGINE_VERSION':importlib.metadata.version('jsonschema'),'SOURCE_SCHEMA_ERRORS':errors['source'],'HANDOFF_SCHEMA_ERRORS':errors['handoff'],'SOURCE_SCHEMA_ERROR_COUNT':len(errors['source']),'HANDOFF_SCHEMA_ERROR_COUNT':len(errors['handoff']),'RESULT':'PASS' if not any(errors.values()) else 'FAIL'}
pathlib.Path(__file__).parent.parent.joinpath('07-schema-validation-final.json').write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out)); raise SystemExit(0 if out['RESULT']=='PASS' else 1)
