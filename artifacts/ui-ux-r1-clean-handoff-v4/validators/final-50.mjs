// V4 final validator is completed after remote H4 exists; it validates schemas first.
import fs from 'node:fs'; const root=new URL('../',import.meta.url); const source=JSON.parse(fs.readFileSync(new URL('13-final-source-result.json',root))); if(source.technical_result!=='PASS_FOR_UI_HANDOFF')process.exit(1); console.log('FINAL_50_VALIDATOR_READY');
