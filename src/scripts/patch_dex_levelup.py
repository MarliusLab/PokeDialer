#!/usr/bin/env python3
"""Binary-level update for the PokeDialer v3.1.4 DEX3 welcome screen.
No repacking/signing. Only operates on a known, fingerprint-checked APK's DEX3.
This script adds a short sound to the one-time popup, and uses existing
MediaPlayer/AssetManager method refs. Original 30 music assets are unmodified.
"""
from pathlib import Path
import struct, hashlib, zlib, zipfile, sys

def u16(b, p): return struct.unpack_from('<H',b,p)[0]
def u32(b, p): return struct.unpack_from('<I',b,p)[0]
def pack16(n): return struct.pack('<H',n&65535)
def pack32(n): return struct.pack('<I',n&0xffffffff)
def uleb(b,p):
 n=0
 for i in range(5):
  c=b[p];p+=1;n|=(c&127)<<(i*7)
  if c<128:return n,p
 raise ValueError('uleb')
def ulebout(n):
 out=bytearray()
 while True:
  c=n&127;n>>=7
  if n:out.append(c|128)
  else:out.append(c);return bytes(out)

class Dex:
 def __init__(self,data):
  self.b=bytearray(data)
  b=self.b
  self.string_cnt,self.string_off,self.type_cnt,self.type_off,self.proto_cnt,self.proto_off,self.field_cnt,self.field_off,self.method_cnt,self.method_off,self.cls_cnt,self.cls_off=struct.unpack_from('<12I',b,56)
  self.strings=[];self.stroffs=[]
  for i in range(self.string_cnt):
   so=u32(b,self.string_off+4*i);self.stroffs.append(so);_,p=uleb(b,so)
   self.strings.append(bytes(b[p:b.index(0,p)]).decode('utf8','replace'))
  self.types=[self.strings[u32(b,self.type_off+4*i)] for i in range(self.type_cnt)]
  self.methods=[]
  for i in range(self.method_cnt):
   cls,pro,name=struct.unpack_from('<HHI',b,self.method_off+i*8)
   rt=u32(b,self.proto_off+pro*12+4);p=u32(b,self.proto_off+pro*12+8)
   args=tuple(self.types[u16(b,p+4+j*2)] for j in range(u32(b,p))) if p else ()
   self.methods.append((self.types[cls],self.strings[name],args,self.types[rt]))
  self.methodmap={m:i for i,m in enumerate(self.methods)}
  self.typemap={t:i for i,t in enumerate(self.types)}
  self.stringmap={s:i for i,s in enumerate(self.strings)}
  self.clsdata={}
  for i in range(self.cls_cnt):
   clidx=u32(b,self.cls_off+i*32);off=u32(b,self.cls_off+i*32+24)
   self.clsdata[self.types[clidx]]=(off,i)
 def method(self,cls,name,args=(),ret='V'):
  key=(cls,name,tuple(args),ret)
  if key not in self.methodmap:raise ValueError('Missing method: '+str(key))
  return self.methodmap[key]
 def type(self,cls):return self.typemap[cls]
 def strid(self,text):return self.stringmap[text]
 def class_methods(self,classname):
  b=self.b;off,_=self.clsdata[classname];sizes=[]
  for i in range(4):k,off=uleb(b,off);sizes.append(k)
  for j in range(sum(sizes[:2])): a,off=uleb(b,off);ac,off=uleb(b,off)
  out={}
  for count in sizes[2:]:
   last=0
   for j in range(count):
    delta,off=uleb(b,off);last+=delta
    access,off=uleb(b,off);po=off;code,off=uleb(b,off)
    out[self.methods[last][1]]=(last,code,po,off)
  return out

def ins_invoke(op,mid,regs):
 assert len(regs)<=5 and all(0<=r<=15 for r in regs)
 reg5=list(regs)+[0]*(5-len(regs))
 return [op|(len(regs)<<8)|(reg5[4]<<12),mid,(reg5[0]|(reg5[1]<<4)|(reg5[2]<<8)|(reg5[3]<<12))]
class Asm:
 def __init__(self):self.words=[];self.labels={};self.fix=[]
 def emit(self,*w):self.words.extend(w)
 def label(self,name):self.labels[name]=len(self.words)
 def branch(self,op,v,label):
  pos=len(self.words);self.emit(op|(v<<8),0);self.fix.append((pos,label))
 def goto(self,label):
  pos=len(self.words);self.emit(0x0029,0);self.fix.append((pos,label))
 def words_final(self):
  for pos,label in self.fix:
   relative=self.labels[label]-pos
   assert -32768<=relative<=32767
   self.words[pos+1]=relative&65535
  return self.words

def code_item(b,co):
 reg,ins,outs,tries,debug,n=struct.unpack_from('<HHHHII',b,co)
 word=list(struct.unpack_from('<%dH'%n,b,co+16))
 return reg,ins,outs,tries,debug,word

def make_code(registers,ins,outs,words,try_handlers=None):
 # try_handlers = (end_addr, catch_type_idx, catch_address)
 b=bytearray(struct.pack('<HHHHII',registers,ins,outs,1 if try_handlers else 0,0,len(words)))
 b.extend(struct.pack('<%dH'%len(words),*words))
 if try_handlers:
  if len(words)&1:b.extend(b'\x00\x00')
  end,excidx,addr=try_handlers
  b.extend(struct.pack('<IHH',0,end,1))
  b.extend(b'\x01\x01')    # encoded_catch_handler_list: one handler, one typed catch
  b.extend(ulebout(excidx))
  b.extend(ulebout(addr))
 return bytes(b)

def patch(dex_bytes):
 x=Dex(dex_bytes);b=x.b
 welcome='Lcom/ajamalen/pokedialer/offline/WelcomeCredits;'
 listener19='Lcom/ajamalen/pokedialer/offline/DiagnosticsActivity$19;'
 listener18='Lcom/ajamalen/pokedialer/offline/DiagnosticsActivity$18;'
 diaga='Lcom/ajamalen/pokedialer/offline/DiagnosticsActivity;'
 mp='Landroid/media/MediaPlayer;'
 print('dex input',len(b),'methods',len(x.methods))
 method1=x.class_methods(welcome)['showOnce'];method2=x.class_methods(listener19)['onCompletion']
 _,co1,codepos1,codeend1=method1
 _,co2,codepos2,codeend2=method2
 reg,ins,outs,tries,debug,orig=code_item(b,co1)
 assert (reg,ins,tries)==(14,1,1) and len(orig)==110
 assert orig[104]==0x1072 and orig[105]==0x003f and orig[106]==0x0004
 assert orig[107]==0x000e and orig[108]==0x000d and orig[109]==0x000e
 old_handler=u32(b,co1+16+len(orig)*2+4)
 assert old_handler>>16==1
 # append sound routine immediately before original :done, inside catch Exception
 m=x.method;t=x.type
 audio=Asm()
 audio.emit(0x001a,x.strid('pd_marlius_welcome_v2')) # const-string v0
 audio.emit(*ins_invoke(0x6e,m('Landroid/content/Context;','getCacheDir',(),'Ljava/io/File;'),[13]))
 audio.emit(0x010c) # move-result-object v1
 audio.emit(0x0222,t('Ljava/io/File;'))
 audio.emit(*ins_invoke(0x70,m('Ljava/io/File;','<init>',('Ljava/io/File;','Ljava/lang/String;')),[2,1,0]))
 audio.emit(*ins_invoke(0x6e,m('Landroid/content/Context;','getAssets',(),'Landroid/content/res/AssetManager;'),[13]))
 audio.emit(0x030c)
 audio.emit(*ins_invoke(0x6e,m('Landroid/content/res/AssetManager;','open',('Ljava/lang/String;',),'Ljava/io/InputStream;'),[3,0]))
 audio.emit(0x040c)
 audio.emit(0x0522,t('Ljava/io/FileOutputStream;'))
 audio.emit(*ins_invoke(0x70,m('Ljava/io/FileOutputStream;','<init>',('Ljava/io/File;',)),[5,2]))
 audio.emit(0x0613,0x1000) # const/16 v6, 4096
 audio.emit(0x6623,t('[B'))   # new-array v6, v6, [B
 audio.label('read_next')
 audio.emit(*ins_invoke(0x6e,m('Ljava/io/InputStream;','read',('[B',),'I'),[4,6]))
 audio.emit(0x070a) # move-result v7
 audio.branch(0x3a,7,'copy_done') # if-ltz v7
 audio.emit(0x0812) # const/4 v8,0
 audio.emit(*ins_invoke(0x6e,m('Ljava/io/FileOutputStream;','write',('[B','I','I')),[5,6,8,7]))
 audio.goto('read_next')
 audio.label('copy_done')
 audio.emit(*ins_invoke(0x6e,m('Ljava/io/FileOutputStream;','close'),[5]))
 audio.emit(*ins_invoke(0x6e,m('Ljava/io/InputStream;','close'),[4]))
 audio.emit(0x0922,t(mp))
 audio.emit(*ins_invoke(0x70,m(mp,'<init>'),[9]))
 audio.emit(*ins_invoke(0x6e,m('Ljava/io/File;','getAbsolutePath',(),'Ljava/lang/String;'),[2]))
 audio.emit(0x0a0c) # move-result-object v10
 audio.emit(*ins_invoke(0x6e,m(mp,'setDataSource',('Ljava/lang/String;',)),[9,10]))
 audio.emit(0x0b22,t(listener18))
 audio.emit(*ins_invoke(0x70,m(listener18,'<init>'),[11]))
 audio.emit(*ins_invoke(0x6e,m(mp,'setOnPreparedListener',('Landroid/media/MediaPlayer$OnPreparedListener;',)),[9,11]))
 audio.emit(0x0c12) # const/4 v12,0 : null DiagnosticsActivity
 audio.emit(0x0b22,t(listener19)) # new-instance v11 re-use
 audio.emit(*ins_invoke(0x70,m(listener19,'<init>',(diaga,)),[11,12]))
 audio.emit(*ins_invoke(0x6e,m(mp,'setOnCompletionListener',('Landroid/media/MediaPlayer$OnCompletionListener;',)),[9,11]))
 audio.emit(*ins_invoke(0x6e,m(mp,'prepareAsync'),[9]))
 new_audio=audio.words_final()
 print('audio words',len(new_audio))
 # shift branches originally going to :done (location 107)
 words=list(orig)
 for start in [4,10,25,43,53,63]:
  assert words[start]&255 in (0x32,0x38,0x39)
  dst=start+struct.unpack('<h',pack16(words[start+1]))[0]
  assert dst==107,(start,dst)
  words[start+1]= (dst-start+len(new_audio))&65535
 full=words[:107]+new_audio+words[107:]
 # typed exception original handler: Ljava/lang/Exception; (index 256) -> address 108 + audio length
 original_trystart=co1+16+len(orig)*2
 trystart=original_trystart + (len(orig)%2)*2
 start,orig_end,handler_off=struct.unpack_from('<IHH',b,trystart)
 assert (start,orig_end,handler_off)==(0,107,1)
 handler_bytes=b[trystart+8:trystart+15]
 assert handler_bytes[:4]==b'\x01\x01\x80\x02',handler_bytes
 catch_idx=256
 c1=make_code(reg,ins,max(outs,4),full,(107+len(new_audio),catch_idx,108+len(new_audio)))
 # callback clean-up when used with null captured Activity; original behavior unchanged otherwise
 rg,si,so,tr,dbg2,owords=code_item(b,co2)
 assert (rg,si,tr,len(owords))==(3,2,0,6)
 assert owords[0]&255==0x54 and owords[2]&255==0x6e
 # append null-check and release into onCompletion for synthetic listener instance
 ondone=[owords[0],owords[1],0x0039,0x0006]+ins_invoke(0x6e,m(mp,'release'),[2])+[0x000e]+owords[2:]
 # if-nez at offset 2, normal branch starts at 8
 assert ondone[2]==0x0039 and len(ondone)==12
 c2=make_code(rg,si,max(so,2),ondone)
 classdata_start=next(u32(b,x.cls_off+i*32+24) for i in range(x.cls_cnt) if u32(b,x.cls_off+i*32+24)>0)
 # use map entry rather than arbitrary first
 oldmap=u32(b,52);nmap=u32(b,oldmap)
 entries=[struct.unpack_from('<HHII',b,oldmap+4+i*12) for i in range(nmap)]
 classdata_start=next(off for typ,unused,size,off in entries if typ==0x2000)
 assert classdata_start==122469 and oldmap==126960
 pad0=(-classdata_start)%4
 new1=classdata_start+pad0
 pad1=(- (new1+len(c1)))%4
 new2=new1+len(c1)+pad1
 insertion=b'\x00'*pad0+c1+b'\x00'*pad1+c2
 shift=len(insertion)
 patched=bytearray(b[:classdata_start]+insertion+b[classdata_start:])
 # class_defs entries hold class_data_off after insertion; update them
 for i in range(x.cls_cnt):
  off=x.cls_off+i*32
  for field in (24,28):
   pos=off+field;v=u32(patched,pos)
   if v>=classdata_start:struct.pack_into('<I',patched,pos,v+shift)
 # encoded methods code_off uleb (old location in shifted class data)
 for oldpos,oldend,newco in ((codepos1,codeend1,new1),(codepos2,codeend2,new2)):
  encoded=ulebout(newco);oldlen=oldend-oldpos
  assert len(encoded)==oldlen,(oldpos,oldlen,len(encoded))
  patched[oldpos+shift:oldend+shift]=encoded
 # map offset and sizes
 newmap=oldmap+shift
 struct.pack_into('<I',patched,52,newmap)
 for i,(typ,unused,size,off) in enumerate(entries):
  pos=newmap+4+i*12
  if typ==0x2001:struct.pack_into('<I',patched,pos+4,size+2)
  if off>=classdata_start:struct.pack_into('<I',patched,pos+8,off+shift)
 struct.pack_into('<I',patched,32,len(patched))
 struct.pack_into('<I',patched,104,u32(b,104)+shift) # data_size
 # String data same-length replacement, both prefs name and asset lookup updated to v3 to show popup once after upgrade
 oldtext=b'pd_marlius_welcome_v2\x00';newtext=b'pd_marlius_welcome_v3\x00'
 assert patched.count(oldtext)==1,patched.count(oldtext)
 patched=patched.replace(oldtext,newtext)
 patched[12:32]=hashlib.sha1(patched[32:]).digest()
 struct.pack_into('<I',patched,8,zlib.adler32(patched[12:])&0xffffffff)
 # static checks
 chk=Dex(patched)
 assert chk.class_methods(welcome)['showOnce'][1]==new1
 assert chk.class_methods(listener19)['onCompletion'][1]==new2
 assert u32(patched,32)==len(patched)
 assert u32(patched,52)==oldmap+shift
 assert b'pd_marlius_welcome_v2\x00' not in patched
 assert patched[:8]==b'dex\n037\x00'
 print('DEX OK',len(b),'->',len(patched),'new method offset',new1,new2,'inserted bytes',shift)
 return bytes(patched)

if __name__=='__main__':
 source=Path(sys.argv[1]);out=Path(sys.argv[2]);
 with zipfile.ZipFile(source) as z: dex=z.read('classes3.dex')
 out.write_bytes(patch(dex))
 print('saved',out)
