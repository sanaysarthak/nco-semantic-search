# app.py
import os, io, datetime
from typing import List
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING
from bson.objectid import ObjectId
import pandas as pd
from dotenv import load_dotenv

from utils import parse_csv_file, dataframe_to_records, normalize_text
from nlp import NCOIndexer

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
PORT = int(os.getenv('PORT', 5000))
INDEX_DIR = os.getenv('INDEX_DIR', './index_store')
MODEL_NAME = os.getenv('MODEL_NAME', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
TOP_K_DEFAULT = int(os.getenv('TOP_K_DEFAULT', '5'))

client = MongoClient(MONGO_URI)
db = client.statathon_db

app = Flask(__name__, static_folder='../static', template_folder='../templates')
CORS(app)
app.config['JSON_SORT_KEYS'] = False

# Collections
col_datasets = db.datasets
col_rows = db.rows
col_nco = db.nco_items
col_syn = db.nco_synonyms
col_audit = db.nco_audit

indexer = NCOIndexer(INDEX_DIR, MODEL_NAME)

# ----------- Pages -----------
@app.route('/')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/upload')
def upload_page():
    return render_template('upload.html')

@app.route('/nco')
def nco_page():
    return render_template('nco_search.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# ----------- Generic dataset APIs -----------
@app.route('/api/ping')
def ping():
    return jsonify({'status': 'ok', 'time': datetime.datetime.utcnow().isoformat()})

@app.route('/api/upload', methods=['POST'])
def upload_dataset():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        name = request.form.get('name') or file.filename
        filename = file.filename
        content_type = file.content_type or ''
        raw = file.read()
        stream = io.StringIO(raw.decode('utf-8', errors='replace'))

        try:
            if filename.lower().endswith('.csv') or 'text/csv' in content_type:
                df = parse_csv_file(stream)
            elif filename.lower().endswith('.json') or 'application/json' in content_type:
                stream.seek(0)
                df = pd.read_json(stream)
            else:
                return jsonify({'error': 'Unsupported file format. Please upload CSV or JSON.'}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to parse file: {str(e)}'}), 400

        ds_doc = {
            'name': name,
            'filename': filename,
            'num_rows': int(len(df)),
            'columns': list(df.columns.astype(str)),
            'uploaded_at': datetime.datetime.utcnow()
        }
        ds_id = col_datasets.insert_one(ds_doc).inserted_id

        recs = dataframe_to_records(df)
        for i in range(0, len(recs), 500):
            batch = recs[i:i+500]
            for r in batch:
                r['_dataset_id'] = ds_id
            col_rows.insert_many(batch)

        preview = df.head(5).to_dict(orient='records')
        return jsonify({
            'ok': True,
            'dataset_id': str(ds_id),
            'num_rows': len(recs),
            'columns': list(df.columns),
            'preview': preview
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/datasets')
def list_datasets():
    out = []
    for d in col_datasets.find().sort('uploaded_at', -1):
        out.append({
            'id': str(d['_id']),
            'name': d.get('name'),
            'filename': d.get('filename'),
            'num_rows': d.get('num_rows'),
            'columns': d.get('columns', [])
        })
    return jsonify({'datasets': out})

@app.route('/api/data')
def get_data():
    dsid = request.args.get('dataset_id')
    page = int(request.args.get('page', 1))
    size = int(request.args.get('page_size', 20))
    if not dsid: return jsonify({'error': 'dataset_id required'}), 400
    try: ds_oid = ObjectId(dsid)
    except: return jsonify({'error': 'invalid dataset_id'}), 400
    q = {'_dataset_id': ds_oid}
    total = col_rows.count_documents(q)
    cur = col_rows.find(q).skip((page-1)*size).limit(size)
    rows = []
    for r in cur:
        r['id'] = str(r.pop('_id'))
        r.pop('_dataset_id', None)
        rows.append(r)
    return jsonify({'rows': rows, 'total': total, 'page': page, 'page_size': size})

@app.route('/api/stats')
def stats():
    dsid = request.args.get('dataset_id')
    if not dsid: return jsonify({'error': 'dataset_id required'}), 400
    try: ds_oid = ObjectId(dsid)
    except: return jsonify({'error':'invalid dataset_id'}),400
    df = pd.DataFrame(list(col_rows.find({'_dataset_id': ds_oid})))
    if df.empty: return jsonify({'error': 'No rows'}), 404
    for c in ['_id','_dataset_id']:
        if c in df.columns: df.drop(columns=[c], inplace=True)
    numeric = df.select_dtypes(include=['number'])
    out = {'numeric_columns': {}, 'categorical_columns': {}}
    for col in numeric.columns:
        s = numeric[col].dropna().astype(float)
        out['numeric_columns'][col] = {
            'count': int(s.count()),
            'mean': float(s.mean()),
            'median': float(s.median()),
            'min': float(s.min()),
            'max': float(s.max()),
            'std': float(s.std() if s.count()>1 else 0.0)
        }
    non = df.select_dtypes(exclude=['number'])
    for col in non.columns:
        top = df[col].value_counts().head(10).to_dict()
        out['categorical_columns'][col] = {str(k): int(v) for k,v in top.items()}
    return jsonify({'stats': out})

# ----------- NCO APIs -----------
@app.route('/api/nco/ingest', methods=['POST'])
def nco_ingest():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    filename = f.filename.lower()
    if filename.endswith('.csv'):
        df = pd.read_csv(f)
    elif filename.endswith('.xlsx') or filename.endswith('.xls'):
        df = pd.read_excel(f)
    else:
        return jsonify({'error': 'Please upload .csv or .xlsx'}), 400

    df.columns = [c.lower() for c in df.columns]
    required = {'code','title','description'}
    if not required.issubset(df.columns):
        return jsonify({'error': 'Missing required columns: code,title,description'}), 400

    hier_cols = [c for c in ['division','group','subgroup','minor','unit'] if c in df.columns]
    def build_path(row):
        parts = []
        for c in hier_cols:
            v = row.get(c)
            if pd.notna(v): parts.append(str(v))
        return ' > '.join(parts)

    norm_rows = []
    for _, row in df.iterrows():
        norm_rows.append({
            'code': str(row['code']).strip(),
            'title': normalize_text(row['title']),
            'description': normalize_text(row['description']),
            'path': build_path(row),
            'ig_at': datetime.datetime.utcnow()
        })

    col_nco.drop()
    if norm_rows:
        col_nco.insert_many(norm_rows)
        col_nco.create_index([('code', ASCENDING)], unique=True)
    return jsonify({'ok': True, 'count': len(norm_rows)})

@app.route('/api/nco/build_index', methods=['POST'])
def nco_build_index():
    items = list(col_nco.find({}, {'code':1,'title':1,'description':1,'path':1}))
    if not items:
        return jsonify({'error': 'No NCO data. Ingest first.'}), 400
    indexer.build(items)
    return jsonify({'ok': True, 'count': len(items)})

@app.route('/api/nco/search')
def nco_search():
    q = request.args.get('q', '').strip()
    top_k = int(request.args.get('top_k', TOP_K_DEFAULT))
    if not q:
        return jsonify({'error':'Query required'}), 400

    # query expansion via synonyms
    syns = [s['term'] for s in col_syn.find({'for': {'$in': q.lower().split()}})]
    expanded = ' '.join([q] + syns)

    try:
        scores, idxs = indexer.search([expanded], top_k=top_k)
    except Exception:
        return jsonify({'error': 'Index not built. Use Admin → Build Index'}), 500

    ids = [indexer.id_map[i] for i in idxs[0] if i != -1]
    conf = [float(max(0.0, min(1.0, s))) for s in scores[0]]
    docs = list(col_nco.find({'_id': {'$in': [ObjectId(x) for x in ids]}}))
    id_to_doc = {str(d['_id']): d for d in docs}
    results = []
    for i, _id in enumerate(ids):
        d = id_to_doc.get(_id)
        if not d: continue
        results.append({
            'code': d.get('code'),
            'title': d.get('title'),
            'description': d.get('description'),
            'path': d.get('path'),
            'confidence': round(conf[i], 4)
        })

    col_audit.insert_one({
        'q': q,
        'expanded': expanded,
        'at': datetime.datetime.utcnow(),
        'top_k': top_k,
        'results': results
    })

    if not results:
        return jsonify({'results': [], 'message': 'No matches. Try different words or add synonyms in Admin.'})

    return jsonify({'results': results})

@app.route('/api/nco/synonyms', methods=['GET','POST','DELETE'])
def nco_synonyms():
    if request.method == 'GET':
        out = []
        for s in col_syn.find().sort('for', ASCENDING):
            out.append({'id': str(s['_id']), 'for': s.get('for'), 'term': s.get('term')})
        return jsonify({'synonyms': out})
    elif request.method == 'POST':
        data = request.get_json(force=True)
        base = (data.get('for') or '').strip().lower()
        term = (data.get('term') or '').strip().lower()
        if not base or not term:
            return jsonify({'error':'"for" and "term" required'}), 400
        col_syn.insert_one({'for': base, 'term': term, 'at': datetime.datetime.utcnow()})
        return jsonify({'ok': True})
    else:
        _id = request.args.get('id')
        if not _id: return jsonify({'error':'id required'}), 400
        col_syn.delete_one({'_id': ObjectId(_id)})
        return jsonify({'ok': True})

@app.route('/api/nco/audit')
def nco_audit():
    items = []
    for a in col_audit.find().sort('at', -1).limit(200):
        a['id'] = str(a.pop('_id'))
        items.append(a)
    return jsonify({'audit': items})

if __name__ == '__main__':
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=PORT, debug=debug)
