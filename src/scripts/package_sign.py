#!/usr/bin/env python3
"""PokeDialer v3.1.5 updater: APK ZIP repack / in-memory v2 signing.
Never commit or ship keystore. v2 signing uses the same X509 cert as v3.1.4.
"""
import sys, zipfile, struct, hashlib, pathlib, io, os, zlib
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PublicFormat
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from patch_dex_levelup import patch
# Paths are supplied by the user. Private signing material is never stored in source control.
OLD = PRIV = CHIME = OUT = None
UINT=lambda i:struct.pack('<I',i)
ULONG=lambda i:struct.pack('<Q',i)
def LP(b):return UINT(len(b))+b

def repack():
 print('Repacking files with byte-identical original content except DEX, manifest and level-up chime...',flush=True)
 source=OLD
 dexnew=patch(zipfile.ZipFile(source).read('classes3.dex'))
 patched=0
 with zipfile.ZipFile(source,'r') as z,zipfile.ZipFile(OUT.with_suffix('.unsigned.apk'),'w',allowZip64=True) as out:
  for info in z.infolist():
   name=info.filename
   if name.startswith('META-INF/') and (name.upper().endswith(('.RSA','.SF','.DSA','.EC')) or name.upper()=='META-INF/MANIFEST.MF'):
    continue
   raw=z.read(info)
   if name=='classes3.dex':raw=dexnew;patched+=1
   if name=='AndroidManifest.xml':
    v1='3.1.4'.encode('utf-16le');v2='3.1.5'.encode('utf-16le'); assert raw.count(v1)==1
    raw=raw.replace(v1,v2)
    oldver=UINT(310004);newver=UINT(310005);assert raw.count(oldver)==1
    raw=raw.replace(oldver,newver);patched+=1
   # remove original extras and reconstruct safe aligned local extras
   cp=zipfile.ZipInfo(name, date_time=info.date_time)
   cp.compress_type=info.compress_type
   cp.external_attr=info.external_attr
   cp.internal_attr=info.internal_attr
   cp.create_system=info.create_system
   cp.comment=info.comment
   cp.flag_bits=0
   cp.extra=b''
   if cp.compress_type==zipfile.ZIP_STORED and not name.endswith('/'):
    # resources and raw PNG/SFX; for compatibility align uncompressed entries to 4 bytes.
    start=out.fp.tell()
    utf8_name=name.encode('utf-8')
    extra_pad=(4-(start+30+len(utf8_name)+4)%4)%4
    cp.extra=struct.pack('<HH',0xd935,extra_pad)+bytes(extra_pad)
   out.writestr(cp,raw,compress_type=cp.compress_type,compresslevel=6)
  out.writestr('assets/pd_marlius_welcome_v3',CHIME.read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
 assert patched==2
 return OUT.with_suffix('.unsigned.apk')

def digest_apk_parts(parts):
 # Android APK Signature Scheme v2: chunked digest 0xA5 and final 0x5A.
 chunks=[]
 for part in parts:
  for off in range(0,len(part),1024*1024):
   chunk=part[off:off+1024*1024]
   chunks.append(hashlib.sha256(b'\xa5'+UINT(len(chunk))+chunk).digest())
 return hashlib.sha256(b'\x5a'+UINT(len(chunks))+b''.join(chunks)).digest()

def split_apk(blob):
 eocd=blob.rfind(b'PK\x05\x06')
 assert eocd>=0 and len(blob)-eocd>=22
 comment_size=struct.unpack_from('<H',blob,eocd+20)[0]
 assert eocd+22+comment_size==len(blob)
 cdsize,cdoff=struct.unpack_from('<II',blob,eocd+12)
 assert cdoff+cdsize==eocd,(cdoff,cdsize,eocd)
 return cdoff,eocd

def make_v2_block(v2):
 pair=ULONG(4+len(v2))+UINT(0x7109871a)+v2
 size=len(pair)+8+16
 return ULONG(size)+pair+ULONG(size)+b'APK Sig Block 42'

def keycert_from_private_bundle():
 with zipfile.ZipFile(PRIV) as z:
  p12=next(n for n in z.namelist() if n.endswith('.p12'))
  pw=next(n for n in z.namelist() if n.startswith('signing/') and n.endswith('.txt'))
  passwd=z.read(pw).decode().strip().encode()
  pk,cert,additional=pkcs12.load_key_and_certificates(z.read(p12),passwd)
  assert pk and cert
  digest=hashlib.sha256(cert.public_bytes(Encoding.DER)).hexdigest()
  assert digest=='7e83b399c16a7963b52cc7dfdb70c84720335f29aaff1bca7bcd378ad42c11df',digest
  return pk,cert

def sign(path):
 unsigned=path.read_bytes();cdoff,eocd=split_apk(unsigned)
 d_eocd=bytearray(unsigned[eocd:]);struct.pack_into('<I',d_eocd,16,cdoff)
 dig=digest_apk_parts((unsigned[:cdoff],unsigned[cdoff:eocd],d_eocd))
 pk,cert=keycert_from_private_bundle()
 if isinstance(pk,rsa.RSAPrivateKey):
  algo=0x0103 # RSASSA-PKCS1-v1_5 SHA-256
  signer=lambda data:pk.sign(data,padding.PKCS1v15(),hashes.SHA256())
 elif isinstance(pk,ec.EllipticCurvePrivateKey):
  algo=0x0201 # ECDSA SHA-256
  signer=lambda data:pk.sign(data,ec.ECDSA(hashes.SHA256()))
 else:raise ValueError('unsupported keystore key type')
 signed_data=(LP(LP(UINT(algo)+LP(dig)))+LP(LP(cert.public_bytes(Encoding.DER)))+LP(b''))
 sig=signer(signed_data)
 spki=cert.public_key().public_bytes(Encoding.DER,PublicFormat.SubjectPublicKeyInfo)
 signer_block=LP(signed_data)+LP(LP(UINT(algo)+LP(sig)))+LP(spki)
 v2=LP(LP(signer_block))
 block=make_v2_block(v2)
 patched_eocd=bytearray(unsigned[eocd:]);struct.pack_into('<I',patched_eocd,16,cdoff+len(block))
 OUT.write_bytes(unsigned[:cdoff]+block+unsigned[cdoff:eocd]+patched_eocd)
 print('v2 signed size',OUT.stat().st_size,'bytes; certificate sha256:',hashlib.sha256(cert.public_bytes(Encoding.DER)).hexdigest())

def verify_v2(path):
 blob=path.read_bytes();cdoff,eocd=split_apk(blob)
 magic=blob[cdoff-16:cdoff];assert magic==b'APK Sig Block 42'
 size=struct.unpack_from('<Q',blob,cdoff-24)[0]
 begin=cdoff-8-size
 assert size==struct.unpack_from('<Q',blob,begin)[0]
 p=begin+8
 sizepair=struct.unpack_from('<Q',blob,p)[0]
 assert struct.unpack_from('<I',blob,p+8)[0]==0x7109871a
 v2=blob[p+12:p+8+sizepair]
 def one_lp(b,p=0):
  n=struct.unpack_from('<I',b,p)[0];return b[p+4:p+4+n],p+4+n
 signers,pos=one_lp(v2)
 signer,pos=one_lp(signers)
 sd,pos=one_lp(signer)
 sigs,pos=one_lp(signer,pos)
 pubkey,pos=one_lp(signer,pos)
 digrecs,idx=one_lp(sd)
 digest,_=one_lp(digrecs)
 algo=struct.unpack_from('<I',digest)[0]
 expected,pos=one_lp(digest,4)
 certrecs,idx=one_lp(sd,idx)
 cert,idx=one_lp(certrecs)
 attr,idx=one_lp(sd,idx)
 sigrec,idx=one_lp(sigs)
 algo2=struct.unpack_from('<I',sigrec)[0]
 signature,idx=one_lp(sigrec,4)
 assert algo==algo2 and algo==0x0103
 assert hashlib.sha256(cert).hexdigest()=='7e83b399c16a7963b52cc7dfdb70c84720335f29aaff1bca7bcd378ad42c11df'
 from cryptography import x509
 certobj=x509.load_der_x509_certificate(cert)
 assert pubkey==certobj.public_key().public_bytes(Encoding.DER,PublicFormat.SubjectPublicKeyInfo)
 certobj.public_key().verify(signature,sd,padding.PKCS1v15(),hashes.SHA256())
 # digest EOCD patched to signing block start
 e=bytearray(blob[eocd:]);struct.pack_into('<I',e,16,begin)
 actual=digest_apk_parts((blob[:begin],blob[cdoff:eocd],e))
 assert actual==expected,'bad v2 content digest'
 # zip integrity, alignment, 30 ogg preserved
 with zipfile.ZipFile(path) as z,zipfile.ZipFile(OLD) as orig:
  bad=z.testzip();assert bad is None,bad
  names=z.namelist();assert 'assets/pd_marlius_welcome_v3' in names
  for n in orig.namelist():
   if n.startswith('assets/audio/') and n.endswith('.ogg'):
    assert z.read(n)==orig.read(n),n
  for info in z.infolist():
   if info.compress_type==zipfile.ZIP_STORED and not info.is_dir():
    name_bytes=info.filename.encode('utf-8');pos=info.header_offset+30+len(name_bytes)+len(info.extra)
    if pos%4:raise ValueError(f'Unaligned stored entry {info.filename}: {pos}')
  m=z.read('AndroidManifest.xml')
  assert '3.1.5'.encode('utf-16le') in m and UINT(310005) in m
  d=z.read('classes3.dex')
  assert hashlib.sha1(d[32:]).digest()==d[12:32]
  assert (zlib.adler32(d[12:])&0xffffffff)==struct.unpack_from('<I',d,8)[0]
  assert d.count(b'pd_marlius_welcome_v3\x00')==1
 print('ALL STATIC VALIDATIONS OK: zip, SHA1, Adler32, v2 certificate/signature/digest, version, audio assets, alignment')
 return True

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description='Build PokeDialer 3.1.5 with level-up jingle from the 3.1.4 APK')
 parser.add_argument('--base',type=pathlib.Path,required=True,help='Signed PokeDialer 3.1.4 APK')
 parser.add_argument('--signing-backup',type=pathlib.Path,required=True,help='Private Marlius signing backup (never publish)')
 parser.add_argument('--sound',type=pathlib.Path,required=True,help='Level-up OGG (the bundled src/audio/pd_marlius_welcome_v3)')
 parser.add_argument('--output',type=pathlib.Path,required=True,help='Signed output APK path')
 args=parser.parse_args()
 OLD=args.base.resolve();PRIV=args.signing_backup.resolve();CHIME=args.sound.resolve();OUT=args.output.resolve()
 for path in (OLD,PRIV,CHIME):
  if not path.is_file(): parser.error('Missing input file: '+str(path))
 if OUT==OLD: parser.error('Output APK must differ from base APK')
 OUT.parent.mkdir(parents=True,exist_ok=True)
 u=repack();sign(u);verify_v2(OUT)
 print(OUT,hashlib.sha256(OUT.read_bytes()).hexdigest())
