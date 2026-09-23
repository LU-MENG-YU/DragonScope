#!/usr/bin/env python3
"""Collector orchestrator for GitHub Actions.

Core behavior is already production-oriented even while all live sources are disabled:
- dynamically load enabled source adapters;
- upsert normalized records by stable id;
- preserve last known good public data if a source fails;
- update source health independently;
- write both JSON and JS bundles atomically enough for a static repository workflow.
"""
from __future__ import annotations
import argparse, importlib, inspect, json, re, sys
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
JS=ROOT/'data'/'public-data.js'; JSON=ROOT/'data'/'public-data.json'; CONF=ROOT/'config'/'sources.json'
MODULES={'cpbl_stats':'collectors.sources.cpbl_stats','cpbl':'collectors.sources.cpbl','news':'collectors.sources.rss','wdragons':'collectors.sources.rss','venues':'collectors.sources.venues','weather':'collectors.sources.weather'}
COLLECTIONS=('players','venues','games','events','lineups')

def load_js_data():
    text=JS.read_text(encoding='utf-8');m=re.search(r'window\.WD_INTEL_DATA\s*=\s*(\{.*\})\s*;\s*$',text,re.S)
    if not m: raise RuntimeError('Cannot parse data/public-data.js')
    return json.loads(m.group(1))

def write_bundle(data):
    payload=json.dumps(data,ensure_ascii=False,indent=2)
    JSON.write_text(payload+'\n',encoding='utf-8')
    JS.write_text('window.WD_INTEL_DATA = '+payload+';\n',encoding='utf-8')

def upsert(existing:list[dict], incoming:list[dict]) -> list[dict]:
    keyed={x['id']:x for x in existing if x.get('id')}
    keyless=[x for x in existing if not x.get('id')]
    for x in incoming:
        if x.get('id'):
            old=keyed.get(x['id'],{})
            keyed[x['id']]={**old,**{k:v for k,v in x.items() if v not in (None,'')}}
        else: keyless.append(x)
    return list(keyed.values())+keyless

def status_map(data): return {x.get('id'):x for x in data.get('source_status',[]) if x.get('id')}

def run_source(source_id,cfg,previous_status,data):
    module_name=MODULES.get(source_id)
    if not module_name: raise RuntimeError(f'No module registered for source {source_id}')
    module=importlib.import_module(module_name)
    params=inspect.signature(module.collect).parameters
    result=module.collect(cfg,data=data) if 'data' in params else module.collect(cfg)
    name=cfg.get('name',source_id.upper());auth=cfg.get('auth','none');mode=cfg.get('mode',Path(cfg.get('adapter','')).stem or 'adapter')
    return result, result.status_record(name=name,auth=auth,mode=mode,previous_success=(previous_status or {}).get('last_success'))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--touch',action='store_true');args=ap.parse_args()
    data=load_js_data(); config=json.loads(CONF.read_text(encoding='utf-8')); statuses=status_map(data)
    if args.touch:
        data.setdefault('meta',{})['generated_at']=datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %z');write_bundle(data);print('Touched bundle.');return
    enabled={k:v for k,v in config.get('sources',{}).items() if v.get('enabled')}
    if not enabled:
        print('No live collectors enabled. Existing dataset preserved.');return
    changed=False
    for sid,cfg in enabled.items():
        try:
            result,status=run_source(sid,cfg,statuses.get(sid),data)
            statuses[sid]=status
            if result.status in {'ok','warn'}:
                for col in COLLECTIONS:
                    incoming=result.payload.get(col,[])
                    if incoming:
                        data[col]=upsert(data.get(col,[]),incoming);changed=True
            print(f'{sid}: {result.status} ({result.record_count} records)')
        except Exception as exc:
            prev=statuses.get(sid,{"id":sid,"name":sid.upper(),"auth":cfg.get('auth','none'),"mode":"adapter","records":0})
            prev={**prev,"status":"bad","last_checked":datetime.now().astimezone().isoformat(timespec='seconds'),"note":f'Collector exception; previous dataset preserved. {exc}'}
            statuses[sid]=prev;print(f'{sid}: bad ({exc})')
    data['source_status']=list(statuses.values())
    meta=data.setdefault('meta',{})
    if changed:
        meta['mode']='PUBLIC_CACHE'
    meta['generated_at']=datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %z')
    write_bundle(data)
    print('Bundle written.' if changed else 'Health updated; existing records preserved.')

if __name__=='__main__': main()
