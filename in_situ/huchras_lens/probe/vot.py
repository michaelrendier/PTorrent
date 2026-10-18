import sys, xml.etree.ElementTree as ET
raw=sys.stdin.read()
if raw.lstrip().startswith('<'):
    root=ET.fromstring(raw); ns={'v':root.tag.split('}')[0][1:]}
    for i in root.iter():
        if i.tag.endswith('INFO') and i.get('name')=='QUERY_STATUS' and i.get('value')!='OK': print('ERR',i.get('value'),(i.text or '')[:300])
    names=[f.get('name') for f in root.iter() if f.tag.endswith('FIELD')]
    print('\t'.join(names))
    for tr in root.iter():
        if tr.tag.endswith('TR'): print('\t'.join((td.text or '').replace('\t',' ') for td in tr))
else: print(raw[:3000])
