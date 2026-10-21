"""Generate a short game-console level-up jingle (original synthesis,
structured after public chiptune notation; not an extracted copyrighted game recording)."""
import numpy as np
import wave, pathlib, subprocess
SR=22050
TICK=1/68.5
notes={"C4":261.63,"D#4":311.13,"E4":329.63,"F4":349.23,
       "A4":440.00,"A#4":466.16,"F5":698.46,"G5":783.99,"D#5":622.25,"A5":880.0}
ch1=[('F4',4,6),('C4',2,4),('F4',2,4),('C4',2,4),('D#4',2,6),('D#4',2,6),('E4',2,6),('F4',8,6)]
ch2=[('A4',4,6),('A4',2,4),('A4',2,4),('A4',2,4),('A#4',2,6),('A#4',2,6),('A#4',2,6),('A4',8,6)]
ch3=[('A5',4,6),('F5',1,4),(None,1,4),('F5',1,4),(None,1,4),('F5',1,4),(None,1,4),('G5',1,6),(None,1,6),('D#5',1,6),(None,1,6),('G5',1,6),(None,1,6),('A5',8,6)]
N=int(2.5*SR)
def render(seq,waveform,volume):
 out=np.zeros(N,dtype=np.float64); cursor=0;phase=0
 for note,count,typ in seq:
  length=int(SR*TICK*count*typ)
  if note:
   t=np.arange(length)/SR
   f=notes[note]
   phase_in=2*np.pi*f*t+phase
   if waveform=='square':
    tone=np.where(np.mod(phase_in/(2*np.pi),1)<0.5,1.0,-1.0)
   elif waveform=='pulse':
    tone=np.where(np.mod(phase_in/(2*np.pi),1)<0.25,1.0,-1.0)
   else:
    tone=2*np.abs(2*np.mod(phase_in/(2*np.pi),1)-1)-1
   # classic per-note envelope and softened onset to avoid clicks
   env=np.exp(-1.5*t/max(length/SR,.015))
   fade=min(90,length//7)
   if fade:env[:fade]*=np.linspace(0,1,fade)
   if fade:env[-fade:]*=np.linspace(1,0,fade)
   if cursor<N:out[cursor:min(cursor+length,N)]+=tone[:min(length,N-cursor)]*env*volume if cursor+length<=N else tone[:N-cursor]*env[:N-cursor]*volume
   phase=(phase+2*np.pi*f*length/SR)%(2*np.pi)
  cursor+=length
 return out
A=render(ch1,'pulse',.32);B=render(ch2,'square',.27);C=render(ch3,'triangle',.18)
L=A+B*.87+C*.68;R=A*.85+B+C*.75
stereo=np.vstack([L,R]).T
# filter lower inaudible pulses and fade tail
stereo=np.clip(stereo,-2,2)
stereo/=max(np.max(np.abs(stereo)),1)*1.1
last=int(SR*.12)
stereo[-last:]*=np.linspace(1,0,last)[:,None]
raw=(np.clip(stereo,-1,1)*32767).astype('<i2')
import argparse
parser=argparse.ArgumentParser(description='Create a retro level-up jingle without game audio samples')
parser.add_argument('--out-dir',type=pathlib.Path,default=pathlib.Path('.'))
parser.add_argument('--name',default='pd_marlius_welcome_v3')
args=parser.parse_args()
out=args.out_dir
out.mkdir(parents=True,exist_ok=True)
wav=out/(args.name+'_preview.wav')
ogg=out/(args.name+'.ogg')
with wave.open(str(wav),'wb') as w:
 w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes(raw.tobytes())
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(wav),'-c:a','libvorbis','-qscale:a','4',str(ogg)],check=True)
print(ogg,ogg.stat().st_size,'duration',len(raw)/SR)
