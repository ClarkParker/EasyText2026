"""Dump node trees, modifiers, texts, actions from a (decompressed) .blend using blender-asset-tracer."""
import sys, json, struct, pathlib
from blender_asset_tracer import blendfile

path = pathlib.Path(sys.argv[1]); outdir = pathlib.Path(sys.argv[2]); outdir.mkdir(exist_ok=True)
bf = blendfile.BlendFile(path)

def s(b):  # bytes -> str
    if isinstance(b, bytes): return b.decode('utf-8', 'replace')
    return b
def g(block, path, default=None, as_str=True):
    try:
        v = block.get(path, default=default, as_str=False)
    except Exception as e:
        return default
    if as_str and isinstance(v, bytes): return v.decode('utf-8','replace')
    return v
def listbase(block, name):
    cur = block.get_pointer((name, b'first')) if block else None
    while cur:
        yield cur
        cur = cur.get_pointer(b'next')
def raw_cstr(block):
    if not block: return None
    d = block.raw_data()
    return d.split(b'\0',1)[0].decode('utf-8','replace')

SUBTYPES = {0:'NONE',13:'UNSIGNED',14:'PERCENTAGE',15:'FACTOR',16|(5<<16):'ANGLE',17|(4<<16):'TIME',18|(1<<16):'DISTANCE',20:'COLOR',21|(1<<16):'TRANSLATION',22:'DIRECTION',26|(5<<16):'EULER',29:'XYZ',29|(1<<16):'XYZ_LENGTH',31:'COORDS', 24:'ACCELERATION', 23:'VELOCITY'}
def subtype_name(v):
    return SUBTYPES.get(v, f'sub{v}')

def sock_value(sock):
    """Return (value, extra) from default_value pointer."""
    dv = sock.get_pointer(b'default_value')
    if not dv: return None, {}
    t = dv.dna_type_name
    try:
        if t == 'bNodeSocketValueFloat':
            return round(g(dv,b'value'),5), {'min':g(dv,b'min'),'max':g(dv,b'max'),'subtype':subtype_name(g(dv,b'subtype'))}
        if t == 'bNodeSocketValueInt':
            return g(dv,b'value'), {'min':g(dv,b'min'),'max':g(dv,b'max'),'subtype':subtype_name(g(dv,b'subtype'))}
        if t == 'bNodeSocketValueBoolean':
            return bool(g(dv,b'value')), {}
        if t == 'bNodeSocketValueVector':
            return [round(x,5) for x in g(dv,b'value')], {'min':g(dv,b'min'),'max':g(dv,b'max'),'subtype':subtype_name(g(dv,b'subtype'))}
        if t == 'bNodeSocketValueRGBA':
            return [round(x,4) for x in g(dv,b'value')], {}
        if t == 'bNodeSocketValueString':
            return g(dv,b'value'), {}
        if t in ('bNodeSocketValueObject','bNodeSocketValueMaterial','bNodeSocketValueCollection','bNodeSocketValueTexture','bNodeSocketValueImage'):
            p = dv.get_pointer(b'value')
            return (s(p.id_name) if p else None), {}
    except Exception as e:
        return f'<err {e}>', {}
    return f'<{t}>', {}

def sock_info(sock, with_values=True):
    flag = g(sock,b'flag',0)
    d = {'name': g(sock,b'name'), 'identifier': g(sock,b'identifier'), 'idname': g(sock,b'idname')}
    desc = g(sock,b'description')
    if desc: d['description'] = desc
    if flag & 2: d['hidden']=True
    if flag & 8: d['unavailable']=True
    if flag & 128: d['hide_value']=True
    if flag & 2048: d['multi_input']=True
    dan = sock.get_pointer(b'default_attribute_name')
    if dan: d['default_attribute_name'] = raw_cstr(dan)
    ad = g(sock,b'attribute_domain',None)
    if ad: d['attribute_domain']=ad
    if with_values:
        v, extra = sock_value(sock)
        if v is not None: d['value']=v
        d.update(extra)
    return d

def storage_info(node):
    st = node.get_pointer(b'storage')
    if not st: return None
    out = {'_type': st.dna_type_name}
    if st.dna_type_name in ('CurveMapping','CurveProfile','ColorBand'):
        return out
    try:
        for k, v in st.items():
            if isinstance(v, bytes): v = v.decode('utf-8','replace')
            if isinstance(k, bytes): k = k.decode()
            if k.startswith('_pad'): continue
            if st.dna_type_name=='NodeInputString' and k=='string':
                p = st.get_pointer(b'string'); v = raw_cstr(p)
            out[k] = v
    except Exception as e:
        out['_err'] = str(e)
    return out

def dump_tree(nt, label):
    lines = []
    nodes = {}
    tree = {'name': label, 'idname': g(nt,b'idname'), 'nodes': [], 'links': [], 'inputs': [], 'outputs': []}
    for io in (b'inputs', b'outputs'):
        for sock in listbase(nt, io):
            tree[io.decode()].append(sock_info(sock))
    for node in listbase(nt, b'nodes'):
        flag = g(node,b'flag',0)
        n = {'name': g(node,b'name'), 'idname': g(node,b'idname'), 'label': g(node,b'label') or '',
             'loc': (round(g(node,b'locx'),1), round(g(node,b'locy'),1)), 'width': round(g(node,b'width'),0),
             'custom1': g(node,b'custom1'), 'custom2': g(node,b'custom2'), 'custom3': round(g(node,b'custom3'),4), 'custom4': round(g(node,b'custom4'),4),
             'muted': bool(flag & 512), 'collapsed': bool(flag & 8)}
        par = node.get_pointer(b'parent')
        if par: n['parent'] = g(par,b'name')
        idp = node.get_pointer(b'id')
        if idp: n['id'] = s(idp.id_name)
        n['storage'] = storage_info(node)
        n['inputs'] = [sock_info(sk) for sk in listbase(node, b'inputs')]
        n['outputs'] = [sock_info(sk, with_values=False) for sk in listbase(node, b'outputs')]
        tree['nodes'].append(n)
    sockname = {}
    for link in listbase(nt, b'links'):
        fn, tn = link.get_pointer(b'fromnode'), link.get_pointer(b'tonode')
        fs, ts = link.get_pointer(b'fromsock'), link.get_pointer(b'tosock')
        tree['links'].append({'from': g(fn,b'name') if fn else None, 'from_sock': g(fs,b'identifier') if fs else None, 'from_sock_name': g(fs,b'name') if fs else None,
                              'to': g(tn,b'name') if tn else None, 'to_sock': g(ts,b'identifier') if ts else None, 'to_sock_name': g(ts,b'name') if ts else None,
                              'muted': bool(g(link,b'flag',0) & 16)})
    return tree

trees = {}
for b in bf.blocks:
    if b.code == b'NT':
        trees[s(b.id_name)[2:]] = dump_tree(b, s(b.id_name)[2:])
    if b.code == b'MA':
        ntp = b.get_pointer(b'nodetree')
        if ntp: trees['MATERIAL:'+s(b.id_name)[2:]] = dump_tree(ntp, 'MATERIAL:'+s(b.id_name)[2:])
json.dump(trees, open(outdir/'trees.json','w'), indent=1, default=str)

# ---- readable text per tree
for name, t in trees.items():
    L = []
    L.append(f"##### TREE {name}  ({t['idname']})  nodes={len(t['nodes'])} links={len(t['links'])}")
    L.append("--- GROUP INPUTS")
    for i, sk in enumerate(t['inputs']):
        L.append(f"  [{i}] {sk['name']!r} ({sk['identifier']}) {sk['idname']} " + json.dumps({k:v for k,v in sk.items() if k not in ('name','identifier','idname')}, default=str))
    L.append("--- GROUP OUTPUTS")
    for i, sk in enumerate(t['outputs']):
        L.append(f"  [{i}] {sk['name']!r} ({sk['identifier']}) {sk['idname']}")
    L.append("--- NODES")
    linked_in = {(l['to'], l['to_sock']) for l in t['links']}
    for n in sorted(t['nodes'], key=lambda n:(n.get('parent') or '', -n['loc'][1], n['loc'][0])):
        extra = []
        if n['label']: extra.append(f"label={n['label']!r}")
        if n.get('parent'): extra.append(f"parent={n['parent']!r}")
        if n.get('id'): extra.append(f"id={n['id']}")
        if n['muted']: extra.append('MUTED')
        if n['custom1'] or n['custom2']: extra.append(f"c1={n['custom1']} c2={n['custom2']}")
        if n['custom3'] or n['custom4']: extra.append(f"c3={n['custom3']} c4={n['custom4']}")
        if n['storage']: extra.append('storage='+json.dumps(n['storage'], default=str))
        L.append(f"NODE {n['idname']} {n['name']!r} loc={n['loc']} " + ' '.join(extra))
        for sk in n['inputs']:
            if sk.get('unavailable'): continue
            lk = (n['name'], sk['identifier']) in linked_in
            if lk: 
                L.append(f"      in  {sk['name']!r}  <- linked")
            elif 'value' in sk:
                L.append(f"      in  {sk['name']!r} = {sk['value']}" + (f"  [{sk.get('subtype')}]" if sk.get('subtype') and sk.get('subtype')!='NONE' else ''))
    L.append("--- LINKS")
    for l in t['links']:
        L.append(f"  {l['from']!r}:{l['from_sock_name']!r} -> {l['to']!r}:{l['to_sock_name']!r}" + (' MUTED' if l['muted'] else ''))
    (outdir/f"tree_{name.replace(':','_')}.txt").write_text('\n'.join(L))
    print(f"wrote tree {name}: {len(t['nodes'])} nodes, {len(t['links'])} links, {len(t['inputs'])} inputs, {len(t['outputs'])} outputs")

# ---- IDProperties (modifier settings)
def idprop(p):
    t = g(p,b'type'); name = g(p,b'name'); sub = g(p,b'subtype'); ln = g(p,b'len')
    data_ptr = p.get_pointer((b'data', b'pointer'))
    if t == 0:  # string
        return name, (raw_cstr(data_ptr) if data_ptr else '')
    if t == 1: return name, g(p,(b'data',b'val'))
    if t == 2: return name, struct.unpack('<f', struct.pack('<i', g(p,(b'data',b'val'))))[0]
    if t == 8: return name, struct.unpack('<d', struct.pack('<ii', g(p,(b'data',b'val')), g(p,(b'data',b'val2'))))[0]
    if t == 5:  # array
        raw = data_ptr.raw_data() if data_ptr else b''
        fmt = {1:'i',2:'f',8:'d'}.get(sub,'B')
        n = ln
        try: return name, list(struct.unpack('<'+fmt*n, raw[:struct.calcsize(fmt)*n]))
        except Exception as e: return name, f'<array err {e}>'
    if t == 6:  # group
        return name, dict(idprop(c) for c in listbase(p, (b'data', b'group')) ) if False else dict(idprop(c) for c in _lb(p))
    if t == 7:
        return name, (s(data_ptr.id_name) if data_ptr else None)
    return name, f'<type {t}>'
def _lb(p):
    cur = p.get_pointer((b'data', b'group', b'first'))
    while cur:
        yield cur
        cur = cur.get_pointer(b'next')

L = []
for b in bf.blocks:
    if b.code == b'OB':
        L.append(f"OBJECT {s(b.id_name)} type={g(b,b'type')} loc={g(b,b'loc')} rot={g(b,b'rot')} scale={g(b,b'size')}")
        data = b.get_pointer(b'data')
        if data: L.append(f"  data: {s(data.id_name)}")
        md = b.get_pointer((b'modifiers', b'first'))
        while md:
            L.append(f"  MODIFIER {md.dna_type_name} name={g(md,(b'modifier',b'name'))!r} type={g(md,(b'modifier',b'type'))} mode={g(md,(b'modifier',b'mode'))}")
            if md.dna_type_name == 'NodesModifierData':
                ng = md.get_pointer(b'node_group')
                L.append(f"    node_group: {s(ng.id_name) if ng else None}")
                props = md.get_pointer((b'settings', b'properties'))
                if props:
                    nm, val = idprop(props)
                    for k, v in val.items():
                        L.append(f"    {k} = {v!r}")
            md = md.get_pointer((b'modifier', b'next'))
        # materials
        try:
            mats = b.get_pointer(b'mat')
            L.append(f"  totcol={g(b,b'totcol')}")
        except Exception as e: pass
    if b.code == b'ME':
        L.append(f"MESH {s(b.id_name)} totvert={g(b,b'totvert')} totpoly={g(b,b'totpoly')} totcol={g(b,b'totcol')}")
    if b.code == b'SC':
        r = b'r'
        L.append(f"SCENE {s(b.id_name)} frames {g(b,(r,b'sfra'))}-{g(b,(r,b'efra'))} cfra={g(b,(r,b'cfra'))} fps={g(b,(r,b'frs_sec'))}/{g(b,(r,b'frs_sec_base'))} res={g(b,(r,b'xsch'))}x{g(b,(r,b'ysch'))}@{g(b,(r,b'size'))}% engine={g(b,(r,b'engine'))!r}")
        cam = b.get_pointer(b'camera'); L.append(f"  camera: {s(cam.id_name) if cam else None}")
        w = b.get_pointer(b'world'); L.append(f"  world: {s(w.id_name) if w else None}")
    if b.code == b'VF':
        L.append(f"FONT {s(b.id_name)} filepath={g(b,b'filepath')!r} packed={'yes' if b.get_pointer(b'packedfile') else 'no'}")
    if b.code == b'GR':
        L.append(f"COLLECTION {s(b.id_name)}")
    if b.code == b'MA':
        L.append(f"MATERIAL {s(b.id_name)} use_nodes={g(b,b'use_nodes')} r,g,b={g(b,b'r')},{g(b,b'g')},{g(b,b'b')}")
(outdir/'objects.txt').write_text('\n'.join(L)); print('\n'.join(L))

# ---- Texts
for b in bf.blocks:
    if b.code == b'TX':
        name = s(b.id_name)[2:]
        txt = '\n'.join((raw_cstr(tl.get_pointer(b'line')) or '') for tl in listbase(b, b'lines'))
        (outdir/f"text_{name}.py").write_text(txt)
        print(f"wrote text {name}: {len(txt)} chars, {txt.count(chr(10))+1} lines")

# ---- Actions
L = []
for b in bf.blocks:
    if b.code == b'AC':
        L.append(f"ACTION {s(b.id_name)} idroot={g(b,b'idroot')} range={g(b,b'frame_start')}-{g(b,b'frame_end')}")
        for fc in listbase(b, b'curves'):
            rp = raw_cstr(fc.get_pointer(b'rna_path'))
            tot = g(fc,b'totvert'); bz = fc.get_pointer(b'bezt')
            keys = []
            if bz:
                for i in range(tot):
                    try:
                        vec = bz.get(b'vec', array_index=i)
                        keys.append((round(vec[3],2), round(vec[4],4)))
                    except Exception as e:
                        keys.append(f'<err {e}>'); break
            L.append(f"  FCURVE {rp}[{g(fc,b'array_index')}] totvert={tot} extend={g(fc,b'extend')} keys={keys}")
        # which ID uses it? check node trees adt
for b in bf.blocks:
    if b.code in (b'NT', b'OB', b'SC', b'MA'):
        adt = b.get_pointer(b'adt')
        if adt:
            act = adt.get_pointer(b'action')
            L.append(f"ANIMDATA on {s(b.id_name)}: action={s(act.id_name) if act else None}")
            for drv in listbase(adt, b'drivers'):
                L.append(f"   DRIVER {raw_cstr(drv.get_pointer(b'rna_path'))}")
(outdir/'actions.txt').write_text('\n'.join(L)); print('\n'.join(L))
