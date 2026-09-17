from pathlib import Path
import urllib.request,concurrent.futures,tarfile
P=Path(__file__).resolve().parents[1]/'sources';P.mkdir(exist_ok=True,parents=True)
urls={
'corpus.tar.gz':'https://codeload.github.com/cltk/lat_text_latin_library/tar.gz/refs/heads/master',
'dictionary.tar.gz':'https://codeload.github.com/IohannesArnold/lewis-short-json/tar.gz/refs/heads/master',
'latin_lemmata_cltk.py':'https://raw.githubusercontent.com/cltk/lat_models_cltk/master/lemmata/latin_lemmata_cltk.py',
'cltk-license':'https://raw.githubusercontent.com/cltk/lat_models_cltk/master/LICENSE',
'neural-config.json':'https://huggingface.co/Ken-Z/latin_SpeechT5/resolve/main/config.json',
'neural-vocab.json':'https://huggingface.co/Ken-Z/latin_SpeechT5/resolve/main/vocab.json',
'neural-model.safetensors':'https://huggingface.co/Ken-Z/latin_SpeechT5/resolve/main/model.safetensors'}
def get(item):
 n,u=item
 if (P/n).exists():return
 d=urllib.request.urlopen(u,timeout=180).read();(P/n).write_bytes(d);print(n,len(d),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:list(ex.map(get,urls.items()))
for n in ['corpus','dictionary']:
 with tarfile.open(P/(n+'.tar.gz')) as t:t.extractall(P,filter='data')
V=Path(__file__).resolve().parents[1]/'dist/vendor';V.mkdir(exist_ok=True)
for n in ['ort.wasm.min.mjs','ort-wasm-simd-threaded.mjs','ort-wasm-simd-threaded.wasm']:
 d=urllib.request.urlopen('https://cdn.jsdelivr.net/npm/onnxruntime-web@1.22.0/dist/'+n,timeout=90).read();(V/n).write_bytes(d)
(V/'LICENSE.txt').write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/microsoft/onnxruntime/v1.22.0/LICENSE').read())
print('Sources and runtime ready',flush=True)
