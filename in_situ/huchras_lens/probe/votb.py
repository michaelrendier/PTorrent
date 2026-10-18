import sys,base64,struct,xml.etree.ElementTree as ET
raw=sys.stdin.read(); root=ET.fromstring(raw)
for i in root.iter():
    if i.tag.endswith('INFO') and i.get('name')=='QUERY_STATUS' and i.get('value')!='OK': print('ERR',i.get('value'),(i.text or '')[:200])
F=[(f.get('name'),f.get('datatype'),f.get('arraysize')) for f in root.iter() if f.tag.endswith('FIELD')]
print('\t'.join(n for n,_,_ in F))
st=[s for s in root.iter() if s.tag.endswith('STREAM')]
if not st: sys.exit()
b=base64.b64decode(''.join(st[0].text.split())); p=0
fmt={'int':('>i',4),'long':('>q',8),'short':('>h',2),'float':('>f',4),'double':('>d',8),'boolean':('>B',1),'unsignedByte':('>B',1)}
while p<len(b):
    row=[]
    for n,t,a in F:
        if t in('char','unicodeChar'):
            w=1 if t=='char' else 2
            if a in(None,'1'): L=1
            elif a.endswith('*'): L=struct.unpack_from('>i',b,p)[0]; p+=4
            else: L=int(a)
            s=b[p:p+L*w]; p+=L*w; row.append(s.decode('latin1' if w==1 else 'utf-16-be'))
        else:
            f,sz=fmt[t]; row.append(str(struct.unpack_from(f,b,p)[0])); p+=sz
    print('\t'.join(row))
