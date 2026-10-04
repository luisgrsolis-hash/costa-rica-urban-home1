import os
import re
import uuid
import mimetypes
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
ADMIN_PIN = os.environ.get('ADMIN_PIN', '')
STORAGE_BUCKET = os.environ.get('STORAGE_BUCKET', 'property-images')

DEFAULT_PROPERTIES = [
    {"id":"p1","title_es":"Villa de Lujo con Vista al Volcán Arenal","title_en":"Luxury Villa with Arenal Volcano View","price":385000,"type":"Villa","location":"La Fortuna","beds":3,"baths":3.5,"area":"2,400 m²","image":"https://images.unsplash.com/photo-1613977257363-707ba9348227?q=80&w=800&auto=format&fit=crop","desc":"Espectacular propiedad rodeada de naturaleza tropical. Cuenta con piscina privada, acabados en maderas preciosas de Costa Rica y vista despejada al Volcán Arenal. Ideal para residencia o rentas de alto rendimiento en Airbnb.","desc_en":"Spectacular property surrounded by tropical nature. Features a private pool, Costa Rican hardwood finishes, and unobstructed Arenal Volcano views. Ideal as a residence or high-performing Airbnb rental.","featured":True,"status":"active"},
    {"id":"p2","title_es":"Quinta Campestre en San Carlos con Río","title_en":"Countryside Farm in San Carlos with River Frontage","price":215000,"type":"Finca","location":"San Carlos","beds":4,"baths":2,"area":"5,000 m²","image":"https://images.unsplash.com/photo-1580587771525-78b9dba3b914?q=80&w=800&auto=format&fit=crop","desc":"Hermosa quinta con casa principal de estilo rústico moderno. Frutales en producción, senderos privados y acceso a río de agua cristalina. Excelente ubicación a 15 min de Ciudad Quesada.","desc_en":"Beautiful countryside estate with a modern-rustic main house, producing fruit trees, private trails, and access to a crystal-clear river. Excellent location just 15 minutes from Ciudad Quesada.","featured":True,"status":"active"},
    {"id":"p3","title_es":"Lote Listo para Construir en Residencial Privado","title_en":"Build-Ready Lot in Private Gated Community","price":85000,"type":"Terreno","location":"San Carlos","beds":0,"baths":0,"area":"850 m²","image":"https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=800&auto=format&fit=crop","desc":"Terreno plano con todos los servicios públicos instalados (agua, electricidad, internet de fibra óptica). Seguridad 24/7 y acceso pavimentado.","desc_en":"Flat lot with all public utilities installed, including water, electricity, and fiber-optic internet. 24/7 security and paved access.","featured":False,"status":"active"},
    {"id":"p4","title_es":"Casa Moderna Familiar de 2 Plantas","title_en":"Modern 2-Story Family Home","price":195000,"type":"Casa","location":"Valle Central","beds":3,"baths":2.5,"area":"320 m²","image":"https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?q=80&w=800&auto=format&fit=crop","desc":"Casa contemporánea con amplios espacios integrados, cocina con sobre de granito, cochera para 2 vehículos y patio trasero techado.","desc_en":"Contemporary home with spacious open-plan areas, granite countertops, a two-car garage, and a covered backyard.","featured":False,"status":"active"}
]


def require_config():
    missing=[]
    if not SUPABASE_URL: missing.append('SUPABASE_URL')
    if not SUPABASE_SERVICE_ROLE_KEY: missing.append('SUPABASE_SERVICE_ROLE_KEY')
    if not ADMIN_PIN: missing.append('ADMIN_PIN')
    if missing:
        raise RuntimeError('Faltan variables de entorno: ' + ', '.join(missing))


def sb_request(method, path, payload=None, headers=None, raw=False):
    require_config()
    url=SUPABASE_URL + path
    h={'apikey':SUPABASE_SERVICE_ROLE_KEY,'Authorization':'Bearer '+SUPABASE_SERVICE_ROLE_KEY}
    if headers: h.update(headers)
    data=None
    if payload is not None and not isinstance(payload,(bytes,bytearray)):
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8')
        h.setdefault('Content-Type','application/json')
    elif isinstance(payload,(bytes,bytearray)):
        data=payload
    req=Request(url,data=data,headers=h,method=method)
    try:
        with urlopen(req,timeout=30) as r:
            body=r.read()
            if raw: return body, r.status, dict(r.headers)
            return json.loads(body.decode('utf-8') or 'null') if body else None
    except HTTPError as e:
        detail=e.read().decode('utf-8','replace')
        raise RuntimeError(f'Supabase {e.code}: {detail}')
    except URLError as e:
        raise RuntimeError(f'No se pudo conectar con Supabase: {e.reason}')


def is_admin():
    return request.headers.get('X-Admin-PIN','') == ADMIN_PIN


def rows():
    data=sb_request('GET','/rest/v1/properties?select=*&order=created_at.desc')
    for d in data:
        d['featured']=bool(d.get('featured'))
        # Keep the frontend field names while using PostgreSQL-safe column names.
        d['desc']=d.get('description')
        d['desc_en']=d.get('description_en')
    return data


def ensure_seed_data():
    data=sb_request('GET','/rest/v1/properties?select=id&limit=1')
    if data:
        return
    for p in DEFAULT_PROPERTIES:
        payload={k:p.get(k) for k in ['id','title_es','title_en','price','type','location','beds','baths','area','image','featured','status']}
        payload['description']=p.get('desc')
        payload['description_en']=p.get('desc_en')
        sb_request('POST','/rest/v1/properties',payload,{'Prefer':'return=minimal'})


@app.get('/')
def home():
    return send_from_directory(ROOT,'index.html')

@app.get('/<path:path>')
def static_files(path):
    if path.startswith('api/'):
        return jsonify(error='Not found'),404
    return send_from_directory(ROOT,path)

@app.get('/api/health')
def health():
    try:
        require_config()
        sb_request('GET','/rest/v1/properties?select=id&limit=1')
        return jsonify(ok=True, database='Supabase PostgreSQL', storage=STORAGE_BUCKET)
    except Exception as e:
        return jsonify(ok=False,error=str(e)),500

@app.get('/api/properties')
def get_properties():
    try:
        ensure_seed_data()
        return jsonify(properties=rows())
    except Exception as e:
        return jsonify(error=str(e)),500

@app.post('/api/admin/verify')
def verify_admin():
    data=request.get_json(silent=True) or {}
    return jsonify(ok=str(data.get('pin','')) == ADMIN_PIN)

@app.post('/api/upload-image')
def upload_image():
    if not is_admin(): return jsonify(error='Unauthorized'),403
    if 'image' not in request.files: return jsonify(error='No se recibió la imagen.'),400
    f=request.files['image']
    if not f.filename: return jsonify(error='No se recibió la imagen.'),400
    allowed={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp','image/gif':'.gif'}
    mime=(f.mimetype or '').lower()
    if mime not in allowed: return jsonify(error='Solo se permiten imágenes JPG, PNG, WEBP o GIF.'),400
    content=f.read()
    if not content or len(content)>10*1024*1024: return jsonify(error='La imagen no es válida o supera 10 MB.'),400
    safe=re.sub(r'[^a-zA-Z0-9_-]+','-',Path(f.filename).stem).strip('-')[:50] or 'property'
    path=f'properties/{safe}-{uuid.uuid4().hex[:12]}{allowed[mime]}'
    try:
        sb_request('POST',f'/storage/v1/object/{STORAGE_BUCKET}/{path}',content,{'Content-Type':mime,'x-upsert':'false'},raw=True)
        public_url=f'{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{path}'
        return jsonify(ok=True,url=public_url,path=path)
    except Exception as e:
        return jsonify(error=str(e)),500

@app.post('/api/properties')
def create_property():
    if not is_admin(): return jsonify(error='Unauthorized'),403
    p=request.get_json(silent=True) or {}
    required=['id','title_es','title_en','price','type','location','image']
    if any(not p.get(k) for k in required): return jsonify(error='Missing required fields'),400
    payload={k:p.get(k) for k in ['id','title_es','title_en','price','type','location','beds','baths','area','image','featured','status']}
    payload['description']=p.get('desc')
    payload['description_en']=p.get('desc_en')
    payload['featured']=bool(payload.get('featured'))
    payload['status']=payload.get('status') or 'active'
    try:
        sb_request('POST','/rest/v1/properties',payload,{'Prefer':'return=minimal'})
        return jsonify(ok=True,properties=rows()),201
    except Exception as e:
        return jsonify(error=str(e)),500

@app.put('/api/properties/<pid>')
def update_property(pid):
    if not is_admin(): return jsonify(error='Unauthorized'),403
    p=request.get_json(silent=True) or {}
    try:
        sb_request('PATCH',f'/rest/v1/properties?id=eq.{pid}',{'status':p.get('status','active')},{'Prefer':'return=minimal'})
        return jsonify(ok=True,properties=rows())
    except Exception as e:
        return jsonify(error=str(e)),500

@app.delete('/api/properties/<pid>')
def delete_property(pid):
    if not is_admin(): return jsonify(error='Unauthorized'),403
    try:
        # Get image first so a deleted listing does not leave a growing storage orphan.
        existing=sb_request('GET',f'/rest/v1/properties?id=eq.{pid}&select=image')
        sb_request('DELETE',f'/rest/v1/properties?id=eq.{pid}',None,{'Prefer':'return=minimal'})
        if existing and existing[0].get('image','').startswith(f'{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/'):
            path=existing[0]['image'].split(f'{STORAGE_BUCKET}/',1)[-1]
            try: sb_request('DELETE',f'/storage/v1/object/{STORAGE_BUCKET}/{path}',None,raw=True)
            except Exception: pass
        return jsonify(ok=True,properties=rows())
    except Exception as e:
        return jsonify(error=str(e)),500

if __name__ == '__main__':
    app.run(host='127.0.0.1',port=int(os.environ.get('PORT','8000')),debug=False)
