using System;
using System.IO;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Globalization;
public static class AssetRaster {
 static Bitmap Load(string f){using(var stream=new MemoryStream(File.ReadAllBytes(f)))using(var b=(Bitmap)Image.FromStream(stream))return b.Clone(new Rectangle(0,0,b.Width,b.Height),PixelFormat.Format32bppArgb);}
 static byte[] Pixels(Bitmap b){var d=b.LockBits(new Rectangle(0,0,b.Width,b.Height),ImageLockMode.ReadOnly,PixelFormat.Format32bppArgb);var p=new byte[b.Width*b.Height*4];for(int y=0;y<b.Height;y++)Marshal.Copy(d.Scan0+y*d.Stride,p,y*b.Width*4,b.Width*4);b.UnlockBits(d);return p;}
 static void Set(Bitmap b,byte[] p){var d=b.LockBits(new Rectangle(0,0,b.Width,b.Height),ImageLockMode.WriteOnly,PixelFormat.Format32bppArgb);for(int y=0;y<b.Height;y++)Marshal.Copy(p,y*b.Width*4,d.Scan0+y*d.Stride,b.Width*4);b.UnlockBits(d);}
 static void Save(Bitmap b,string f){Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(f)));b.Save(f,ImageFormat.Png);}
 static GraphicsPath Shape(string spec){var p=new GraphicsPath(FillMode.Alternate);var ts=Regex.Matches(spec??"",@"[MLCQZER]|-?\d+(?:\.\d+)?");int i=0;float x=0,y=0;Func<float> num=()=>float.Parse(ts[i++].Value,CultureInfo.InvariantCulture);while(i<ts.Count){string c=ts[i++].Value;if(c=="M"){x=num();y=num();p.StartFigure();}else if(c=="L"){float a=num(),b=num();p.AddLine(x,y,a,b);x=a;y=b;}else if(c=="C"){float a=num(),b=num(),cc=num(),d=num(),e=num(),f=num();p.AddBezier(x,y,a,b,cc,d,e,f);x=e;y=f;}else if(c=="Q"){float a=num(),b=num(),e=num(),f=num();p.AddBezier(x,y,x+2*(a-x)/3,y+2*(b-y)/3,e+2*(a-e)/3,f+2*(b-f)/3,e,f);x=e;y=f;}else if(c=="E"){float a=num(),b=num(),w=num(),h=num();p.AddEllipse(a,b,w,h);}else if(c=="R"){float a=num(),b=num(),w=num(),h=num();p.AddRectangle(new RectangleF(a,b,w,h));}else if(c=="Z")p.CloseFigure();}return p;}
 static Bitmap Mask(int w,int h,int ox,int oy,string spec,bool full,bool union=false){var b=new Bitmap(w,h,PixelFormat.Format32bppArgb);if(String.IsNullOrWhiteSpace(spec)){if(full)using(var g=Graphics.FromImage(b))g.Clear(Color.White);return b;}using(var hi=new Bitmap(w*4,h*4,PixelFormat.Format32bppArgb)){using(var g=Graphics.FromImage(hi)){g.SmoothingMode=SmoothingMode.AntiAlias;g.ScaleTransform(4,4);g.TranslateTransform(-ox,-oy);using(var p=Shape(spec)){if(union)p.FillMode=FillMode.Winding;g.FillPath(Brushes.White,p);}}using(var g=Graphics.FromImage(b)){g.InterpolationMode=InterpolationMode.HighQualityBicubic;g.DrawImage(hi,0,0,w,h);}}return b;}
 static double[] Blur(double[] a,int w,int h,int r){if(r<=0)return a;var b=new double[a.Length];var o=new double[a.Length];for(int y=0;y<h;y++){double sum=0;for(int x=-r;x<=r;x++)sum+=a[y*w+Math.Clamp(x,0,w-1)];for(int x=0;x<w;x++){b[y*w+x]=sum/(2*r+1);sum-=a[y*w+Math.Clamp(x-r,0,w-1)];sum+=a[y*w+Math.Clamp(x+r+1,0,w-1)];}}for(int x=0;x<w;x++){double sum=0;for(int y=-r;y<=r;y++)sum+=b[Math.Clamp(y,0,h-1)*w+x];for(int y=0;y<h;y++){o[y*w+x]=sum/(2*r+1);sum-=b[Math.Clamp(y-r,0,h-1)*w+x];sum+=b[Math.Clamp(y+r+1,0,h-1)*w+x];}}return o;}
 public static void Prepare(string source,string cropFile,string contourFile,string editFile,string blendFile,int[] rect,string outline,string repair,int feather){
  using(var src=Load(source)){int x=rect[0],y=rect[1],w=rect[2]-x,h=rect[3]-y;if(w<=0||h<=0||x<0||y<0||rect[2]>src.Width||rect[3]>src.Height)throw new ArgumentException("Crop outside source");
   using(var crop=new Bitmap(w,h,PixelFormat.Format32bppArgb)){var p=Pixels(src);var q=Pixels(crop);for(int yy=0;yy<h;yy++)Buffer.BlockCopy(p,((yy+y)*src.Width+x)*4,q,yy*w*4,w*4);Set(crop,q);Save(crop,cropFile);}
   using(var contour=Mask(w,h,x,y,outline,true))Save(contour,contourFile);
   using(var edit=Mask(w,h,x,y,repair,false,true))using(var blend=new Bitmap(w,h,PixelFormat.Format32bppArgb)){var p=Pixels(edit);var bp=Pixels(blend);var field=new double[w*h];for(int k=0;k<field.Length;k++)field[k]=p[k*4+3]/255.0;field=Blur(field,w,h,feather);for(int k=0;k<field.Length;k++){byte mask=(byte)Math.Round(field[k]*255);int i=k*4;int a=p[i+3];p[i]=p[i+1]=p[i+2]=255;p[i+3]=(byte)(255-a);bp[i]=bp[i+1]=bp[i+2]=255;bp[i+3]=(byte)(255-mask);}Set(edit,p);Set(blend,bp);Save(edit,editFile);Save(blend,blendFile);}
  }
 }
 public static string Export(string source,string candidate,string contourFile,string blendFile,string dst,string route,string alphaSource,string candidateKind,int pad){
  using(var s=Load(source))using(var c=Load(candidate))using(var mask=Load(contourFile))using(var blend=Load(blendFile))using(var fitted=new Bitmap(s.Width,s.Height,PixelFormat.Format32bppArgb))using(var result=new Bitmap(s.Width+2*pad,s.Height+2*pad,PixelFormat.Format32bppArgb)){
   if(route=="repair"&&candidateKind=="composite"&&(c.Width!=s.Width||c.Height!=s.Height))throw new ArgumentException("Local composite must retain the native canvas");
   if(c.Width==s.Width&&c.Height==s.Height)Set(fitted,Pixels(c));else using(var g=Graphics.FromImage(fitted)){g.CompositingMode=CompositingMode.SourceCopy;g.InterpolationMode=InterpolationMode.HighQualityBicubic;g.PixelOffsetMode=PixelOffsetMode.HighQuality;g.DrawImage(c,0,0,s.Width,s.Height);}
   var p=Pixels(s);var q=Pixels(fitted);var mp=Pixels(mask);var bp=Pixels(blend);var output=Pixels(result);long protectedPixels=0,protectedChanged=0,foreground=0;int alphaAgreement=0;
   for(int y=0;y<s.Height;y++)for(int x=0;x<s.Width;x++){int i=(y*s.Width+x)*4,j=((y+pad)*result.Width+x+pad)*4;int a=route=="rebuild"||alphaSource=="automatic"?q[i+3]:mp[i+3];if(a>8)foreground++;if(route=="extract"&&alphaSource=="contour"&&Math.Abs(q[i+3]-mp[i+3])>2)alphaAgreement++;
    double f=(255-bp[i+3])/255.0;bool keep=route=="extract"||(route=="repair"&&f==0);
    for(int ch=0;ch<3;ch++){byte value;if(keep)value=p[i+ch];else if(route=="repair"&&candidateKind=="raw")value=(byte)Math.Clamp(Math.Round(p[i+ch]*(1-f)+q[i+ch]*f),0,255);else value=q[i+ch];output[j+ch]=a==0?(byte)0:value;}
    output[j+3]=(byte)a;if(keep&&a>=240){protectedPixels++;for(int ch=0;ch<3;ch++)if(output[j+ch]!=p[i+ch]){protectedChanged++;break;}}
   }
   Set(result,output);Save(result,dst);return "{\"width\":"+result.Width+",\"height\":"+result.Height+",\"foreground_pixels\":"+foreground+",\"protected_pixels\":"+protectedPixels+",\"protected_changed_pixels\":"+protectedChanged+",\"candidate_contour_disagreement_pixels\":"+alphaAgreement+"}";
  }
 }
 public static void ReviewPlate(string source,string dst){using(var s=Load(source)){double scale=Math.Min(1,640.0/s.Width);int w=(int)Math.Round(s.Width*scale),h=(int)Math.Round(s.Height*scale);using(var o=new Bitmap(w*3,h,PixelFormat.Format32bppArgb))using(var g=Graphics.FromImage(o)){Color[] colors={Color.FromArgb(245,240,226),Color.FromArgb(30,39,51),Color.FromArgb(155,65,170)};for(int i=0;i<3;i++){using(var brush=new SolidBrush(colors[i]))g.FillRectangle(brush,i*w,0,w,h);g.DrawImage(s,new Rectangle(i*w,0,w,h));}Save(o,dst);}}}
 public static void Layout(string source,string dst,string[] files,int[] boxes,bool originalBackdrop){using(var s=Load(source))using(var o=new Bitmap(s.Width,s.Height,PixelFormat.Format32bppArgb))using(var g=Graphics.FromImage(o)){g.Clear(Color.FromArgb(255,34,43,56));if(originalBackdrop)g.DrawImageUnscaled(s,0,0);for(int i=0;i<files.Length;i++)using(var b=Load(files[i]))g.DrawImage(b,new Rectangle(boxes[i*4],boxes[i*4+1],boxes[i*4+2],boxes[i*4+3]));Save(o,dst);}}
}
