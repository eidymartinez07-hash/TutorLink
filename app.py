import os, csv, io, secrets, smtplib, re
from datetime import datetime, date, timedelta
from functools import wraps
from email.message import EmailMessage
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, func
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
app=Flask(__name__)
app.config.update(SECRET_KEY=os.getenv('SECRET_KEY','DEV_ONLY_CHANGE_ME'), SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL','mysql+pymysql://tutorlink:tutorlink@localhost:3306/tutorlink?charset=utf8mb4'),SQLALCHEMY_TRACK_MODIFICATIONS=False,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax')
app.config['SESSION_COOKIE_SECURE']=os.getenv('HTTPS','1' if os.getenv('RAILWAY_ENVIRONMENT') else '0')=='1'
db=SQLAlchemy(app)

class User(db.Model):
 numero_control=db.Column(db.String(20),unique=True,nullable=True)
 id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(140),nullable=False); email=db.Column(db.String(180),unique=True,nullable=False); password=db.Column(db.String(255),nullable=False); role=db.Column(db.String(20),nullable=False); career=db.Column(db.String(100),default=''); semester=db.Column(db.Integer); tutor_id=db.Column(db.Integer,db.ForeignKey('user.id')); active=db.Column(db.Boolean,default=True)
class Session(db.Model):
 id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(160),nullable=False); starts=db.Column(db.DateTime,nullable=False); location=db.Column(db.String(120),default=''); tutor_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); description=db.Column(db.Text,default='')
class Attendance(db.Model):
 id=db.Column(db.Integer,primary_key=True); session_id=db.Column(db.Integer,db.ForeignKey('session.id'),nullable=False); student_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); present=db.Column(db.Boolean,default=False); __table_args__=(UniqueConstraint('session_id','student_id'),)
class Activity(db.Model):
 id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(160),nullable=False); prompt=db.Column(db.Text,nullable=False); tutor_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); due=db.Column(db.Date)
class Submission(db.Model):
 id=db.Column(db.Integer,primary_key=True); activity_id=db.Column(db.Integer,db.ForeignKey('activity.id'),nullable=False); student_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); answer=db.Column(db.Text,nullable=False); feedback=db.Column(db.Text,default=''); status=db.Column(db.String(25),default='entregado'); created=db.Column(db.DateTime,default=datetime.utcnow); __table_args__=(UniqueConstraint('activity_id','student_id'),)
class Referral(db.Model):
 id=db.Column(db.Integer,primary_key=True); student_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); tutor_id=db.Column(db.Integer,db.ForeignKey('user.id')); subject=db.Column(db.String(160),nullable=False); details=db.Column(db.Text,nullable=False); status=db.Column(db.String(25),default='pendiente'); response=db.Column(db.Text,default=''); created=db.Column(db.DateTime,default=datetime.utcnow)
class Notification(db.Model):
 id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); message=db.Column(db.String(255),nullable=False); created=db.Column(db.DateTime,default=datetime.utcnow); seen=db.Column(db.Boolean,default=False); event_key=db.Column(db.String(100),unique=True)

@app.before_request
def csrf_guard():
 if 'csrf' not in session: session['csrf']=secrets.token_urlsafe(32)
 if request.method=='POST' and request.form.get('_csrf')!=session['csrf']: abort(400,'Token de seguridad inválido')
@app.context_processor
def globals_ctx():
 u=db.session.get(User,session.get('uid')) if session.get('uid') else None
 return {'me':u,'csrf':session.get('csrf'),'today':date.today()}
def login_required(f):
 @wraps(f)
 def wrapped(*a,**kw):
  if not session.get('uid'): return redirect(url_for('login'))
  u=db.session.get(User,session['uid'])
  if not u or not u.active: session.clear(); return redirect(url_for('login'))
  return f(*a,**kw)
 return wrapped
def roles(*allowed):
 def decorator(f):
  @wraps(f)
  @login_required
  def wrapped(*a,**kw):
   if db.session.get(User,session['uid']).role not in allowed: abort(403)
   return f(*a,**kw)
  return wrapped
 return decorator
def current(): return db.session.get(User,session['uid'])
def students_for(tutor): return User.query.filter_by(role='estudiante',tutor_id=tutor.id,active=True).order_by(User.name).all()
def can_view_student(student):
 u=current(); return u.role=='coordinacion' or (u.role=='tutor' and student.tutor_id==u.id) or u.id==student.id
def notify(uid,msg,key=None):
 if key and Notification.query.filter_by(event_key=key).first(): return
 db.session.add(Notification(user_id=uid,message=msg,event_key=key))

@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  role=request.form.get('role','')
  u=None
  if role=='estudiante':
   u=User.query.filter_by(numero_control=request.form.get('numero_control','').strip(),role=role,active=True).first()
  elif role in ('tutor','coordinacion'):
   u=User.query.filter_by(email=request.form.get('email','').strip().lower(),role=role,active=True).first()
  elif not role: # Compatibilidad temporal con el formulario anterior
   u=User.query.filter_by(email=request.form.get('email','').strip().lower(),active=True).first()
   if u and u.role=='estudiante' and u.numero_control: u=None
  if u and check_password_hash(u.password,request.form.get('password','')):
   session.clear(); session['uid']=u.id; session['csrf']=secrets.token_urlsafe(32); return redirect(url_for('home'))
  flash('Credenciales incorrectas.','error')
 return render_template('login.html')
@app.route('/register',methods=['GET','POST'])
def register():
 if session.get('uid'): return redirect(url_for('home'))
 if request.method=='POST':
  name=request.form.get('name','').strip()
  email=request.form.get('email','').strip().lower()
  password=request.form.get('password','')
  confirm=request.form.get('confirm','')
  numero_control=request.form.get('numero_control','').strip()
  if not 2<=len(name)<=140 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>180:
   flash('Revisa tu nombre y correo electrónico.','error')
  elif not re.fullmatch(r'[0-9]{8}',numero_control):
   flash('Ingresa un número de control de 8 dígitos.','error')
  elif User.query.filter_by(numero_control=numero_control).first():
   flash('El número de control ya está registrado.','error')
  elif not re.fullmatch(r'[0-9]{8,12}',password) or password!=confirm:
   flash('El NIP debe tener de 8 a 12 dígitos y coincidir en ambos campos.','error')
  elif User.query.filter_by(email=email).first():
   flash('Este correo ya tiene una cuenta. Inicia sesión.','error')
  else:
   u=User(name=name,email=email,numero_control=numero_control,password=generate_password_hash(password),role='estudiante',active=True)
   db.session.add(u)
   try:
    db.session.commit()
   except Exception:
    db.session.rollback()
    flash('No fue posible registrar la cuenta. Comprueba el correo.','error')
   else:
    session.clear(); session['uid']=u.id; session['csrf']=secrets.token_urlsafe(32)
    flash('Cuenta creada. Coordinación asignará tu tutor académico.')
    return redirect(url_for('home'))
 return render_template('register.html')

@app.post('/logout')
@login_required
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/')
@login_required
def home():
 u=current(); notes=Notification.query.filter_by(user_id=u.id).order_by(Notification.created.desc()).limit(6).all()
 if u.role=='estudiante':
  activities=Activity.query.filter_by(tutor_id=u.tutor_id).order_by(Activity.id.desc()).all() if u.tutor_id else []
  subs={s.activity_id:s for s in Submission.query.filter_by(student_id=u.id).all()}
  refs=Referral.query.filter_by(student_id=u.id).order_by(Referral.id.desc()).all()
  sessions=Session.query.filter_by(tutor_id=u.tutor_id).order_by(Session.starts.desc()).limit(15).all() if u.tutor_id else []
  return render_template('student.html',activities=activities,subs=subs,refs=refs,sessions=sessions,notes=notes)
 if u.role=='tutor':
  studs=students_for(u); sessions=Session.query.filter_by(tutor_id=u.id).order_by(Session.starts.desc()).all(); acts=Activity.query.filter_by(tutor_id=u.id).order_by(Activity.id.desc()).all(); refs=Referral.query.filter_by(tutor_id=u.id).order_by(Referral.id.desc()).all()
  return render_template('tutor.html',studs=studs,sessions=sessions,acts=acts,refs=refs,notes=notes)
 users=User.query.order_by(User.role,User.name).all(); refs=Referral.query.order_by(Referral.id.desc()).all(); tutors=User.query.filter_by(role='tutor',active=True).all()
 return render_template('coord.html',users=users,refs=refs,tutors=tutors,notes=notes)

@app.post('/users/create')
@roles('coordinacion')
def create_user():
 role=request.form.get('role'); email=request.form.get('email','').strip().lower(); password=request.form.get('password',''); name=request.form.get('name','').strip()
 numero_control=request.form.get('numero_control','').strip() if role=='estudiante' else None
 valid_password=bool(re.fullmatch(r'[0-9]{8,12}',password)) if role=='estudiante' else len(password)>=10
 if role not in ('estudiante','tutor','coordinacion') or not valid_password or not 2<=len(name)<=140 or len(email)>180 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or User.query.filter_by(email=email).first():
  flash('Revisa nombre, rol, correo y contraseña.','error'); return redirect(url_for('home'))
 if role=='estudiante' and (not re.fullmatch(r'[0-9]{8}',numero_control) or User.query.filter_by(numero_control=numero_control).first()):
  flash('Número de control inválido o duplicado.','error'); return redirect(url_for('home'))
 try:
  tutor_id=int(request.form['tutor_id']) if role=='estudiante' and request.form.get('tutor_id') else None
  semester=int(request.form['semester']) if role=='estudiante' and request.form.get('semester') else None
  if semester is not None and not 1<=semester<=15: raise ValueError()
 except ValueError:
  flash('Revisa semestre y tutor.','error'); return redirect(url_for('home'))
 if tutor_id and not User.query.filter_by(id=tutor_id,role='tutor',active=True).first(): abort(400)
 try:
  db.session.add(User(name=name,email=email,numero_control=numero_control,password=generate_password_hash(password),role=role,career=request.form.get('career','')[:100] if role=='estudiante' else '',semester=semester,tutor_id=tutor_id)); db.session.commit()
 except Exception:
  db.session.rollback(); app.logger.exception('Error al crear cuenta'); flash('No se pudo crear la cuenta.','error'); return redirect(url_for('home'))
 flash('Cuenta creada.'); return redirect(url_for('home'))
@app.post('/users/<int:uid>/assign')
@roles('coordinacion')
def assign(uid):
 student=db.get_or_404(User,uid)
 if student.role!='estudiante': abort(400)
 tutor=db.get_or_404(User,int(request.form['tutor_id']))
 if tutor.role!='tutor': abort(400)
 student.tutor_id=tutor.id; db.session.commit(); flash('Tutor asignado.'); return redirect(url_for('home'))
@app.post('/sessions/create')
@roles('tutor')
def session_create():
 starts=datetime.fromisoformat(request.form['starts']); db.session.add(Session(title=request.form['title'].strip(),starts=starts,location=request.form.get('location',''),description=request.form.get('description',''),tutor_id=current().id)); db.session.commit(); flash('Sesión programada.'); return redirect(url_for('home'))
@app.route('/sessions/<int:sid>/attendance',methods=['GET','POST'])
@roles('tutor')
def attendance(sid):
 s=db.get_or_404(Session,sid)
 if s.tutor_id!=current().id: abort(403)
 studs=students_for(current())
 if request.method=='POST':
  present={int(v) for v in request.form.getlist('present')}
  for student in studs:
   a=Attendance.query.filter_by(session_id=s.id,student_id=student.id).first()
   if not a: a=Attendance(session_id=s.id,student_id=student.id); db.session.add(a)
   a.present=student.id in present
  db.session.commit(); flash('Asistencia guardada.'); return redirect(url_for('home'))
 records={a.student_id:a.present for a in Attendance.query.filter_by(session_id=s.id).all()}
 return render_template('attendance.html',s=s,studs=studs,records=records)
@app.post('/activities/create')
@roles('tutor')
def activity_create():
 due=date.fromisoformat(request.form['due']) if request.form.get('due') else None
 db.session.add(Activity(title=request.form['title'].strip(),prompt=request.form['prompt'].strip(),tutor_id=current().id,due=due)); db.session.commit(); flash('Actividad publicada.'); return redirect(url_for('home'))
@app.route('/activities/<int:aid>',methods=['GET','POST'])
@roles('estudiante')
def activity_answer(aid):
 a=db.get_or_404(Activity,aid)
 if a.tutor_id!=current().tutor_id: abort(403)
 sub=Submission.query.filter_by(activity_id=aid,student_id=current().id).first()
 if request.method=='POST':
  if not sub: sub=Submission(activity_id=aid,student_id=current().id); db.session.add(sub)
  sub.answer=request.form['answer'].strip(); sub.status='entregado'; sub.created=datetime.utcnow(); db.session.commit(); notify(a.tutor_id,'Nueva entrega de cuadernillo: '+a.title); db.session.commit(); flash('Respuesta guardada.'); return redirect(url_for('home'))
 return render_template('activity.html',a=a,sub=sub)
@app.route('/activities/<int:aid>/review',methods=['GET','POST'])
@roles('tutor')
def review(aid):
 a=db.get_or_404(Activity,aid)
 if a.tutor_id!=current().id: abort(403)
 subs=Submission.query.filter_by(activity_id=aid).all()
 subs=[s for s in subs if db.session.get(User,s.student_id).tutor_id==current().id]
 if request.method=='POST':
  s=db.get_or_404(Submission,int(request.form['submission_id']))
  if s not in subs: abort(403)
  s.feedback=request.form.get('feedback','').strip(); s.status='revisado'; notify(s.student_id,'Tu actividad fue revisada: '+a.title); db.session.commit(); flash('Revisión guardada.'); return redirect(url_for('review',aid=aid))
 return render_template('review.html',a=a,subs=subs)
@app.post('/referrals/create')
@roles('estudiante')
def referral_create():
 u=current(); r=Referral(student_id=u.id,tutor_id=u.tutor_id,subject=request.form['subject'].strip(),details=request.form['details'].strip()); db.session.add(r)
 if u.tutor_id: notify(u.tutor_id,'Nueva solicitud de apoyo de '+u.name)
 db.session.commit(); flash('Solicitud registrada.'); return redirect(url_for('home'))
@app.post('/referrals/<int:rid>/update')
@roles('tutor','coordinacion')
def referral_update(rid):
 r=db.get_or_404(Referral,rid); u=current()
 if u.role=='tutor' and r.tutor_id!=u.id: abort(403)
 status=request.form['status']
 if status not in ('pendiente','en_revision','canalizada','atendida'): abort(400)
 r.status=status; r.response=request.form.get('response','').strip(); notify(r.student_id,'Tu solicitud #'+str(r.id)+' cambió a '+status); db.session.commit(); flash('Solicitud actualizada.'); return redirect(url_for('home'))
@app.get('/reports/attendance.csv')
@roles('tutor','coordinacion')
def report():
 u=current(); q=db.session.query(Session,Attendance,User).join(Attendance,Attendance.session_id==Session.id).join(User,User.id==Attendance.student_id)
 if u.role=='tutor': q=q.filter(Session.tutor_id==u.id)
 f=io.StringIO(); w=csv.writer(f); w.writerow(['Sesion','Fecha','Estudiante','Presente'])
 for s,a,student in q.order_by(Session.starts.desc()).all(): w.writerow([s.title,s.starts.isoformat(),student.name,'Sí' if a.present else 'No'])
 return Response('\ufeff'+f.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=asistencias_tutorlink.csv'})

@app.cli.command('init-db')
def init_db(): db.create_all(); print('Tablas creadas')
@app.cli.command('create-admin')
def create_admin():
 import getpass
 email=input('Correo coordinación: ').strip().lower(); name=input('Nombre: ').strip(); pwd=getpass.getpass('Contraseña (mínimo 10 caracteres): ')
 if len(pwd)<10: raise SystemExit('Contraseña demasiado corta')
 if User.query.filter_by(email=email).first(): raise SystemExit('Correo ya existe')
 db.session.add(User(name=name,email=email,password=generate_password_hash(pwd),role='coordinacion')); db.session.commit(); print('Cuenta creada')
@app.cli.command('reset-password')
def reset_password():
 import getpass
 email=input('Correo de la cuenta: ').strip().lower()
 u=User.query.filter_by(email=email).first()
 if not u: raise SystemExit('No existe ese correo')
 pwd=getpass.getpass('Nueva contraseña (mínimo 10 caracteres): ')
 if len(pwd)<10: raise SystemExit('Contraseña demasiado corta')
 u.password=generate_password_hash(pwd); db.session.commit(); print('Contraseña actualizada')

@app.cli.command('send-reminders')
def send_reminders():
 tomorrow=datetime.utcnow()+timedelta(days=1); end=tomorrow+timedelta(days=1)
 count=0
 for s in Session.query.filter(Session.starts>=tomorrow,Session.starts<end).all():
  for u in students_for(db.session.get(User,s.tutor_id)):
   key=f'reminder-{s.id}-{u.id}'
   if Notification.query.filter_by(event_key=key).first(): continue
   msg=f'Recordatorio: {s.title} el {s.starts:%d/%m/%Y %H:%M}'
   notify(u.id,msg,key); count+=1
   if os.getenv('SMTP_HOST'):
    em=EmailMessage(); em['Subject']='TutorLink: recordatorio de tutoría'; em['From']=os.getenv('SMTP_FROM') or os.getenv('SMTP_USER'); em['To']=u.email; em.set_content(msg)
    try:
     with smtplib.SMTP(os.getenv('SMTP_HOST'),int(os.getenv('SMTP_PORT','587')),timeout=15) as smtp:
      smtp.starttls(); smtp.login(os.getenv('SMTP_USER'),os.getenv('SMTP_PASSWORD')); smtp.send_message(em)
    except Exception as ex: print('Correo no enviado:',ex)
 db.session.commit(); print(f'{count} recordatorios registrados')
if __name__=='__main__': app.run(debug=os.getenv('FLASK_DEBUG')=='1')
