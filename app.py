  studs=students_for(u); sessions=Session.query.filter_by(tutor_id=u.id).order_by(Session.starts.desc()).all(); acts=Activity.query.filter_by(tutor_id=u.id).order_by(Activity.id.desc()).all(); refs=Referral.query.filter_by(tutor_id=u.id).order_by(Referral.id.desc()).all()
  return render_template('tutor.html',studs=studs,sessions=sessions,acts=acts,refs=refs,notes=notes)
 users=User.query.order_by(User.role,User.name).all(); refs=Referral.query.order_by(Referral.id.desc()).all(); tutors=User.query.filter_by(role='tutor',active=True).all()
 return render_template('coord.html',users=users,refs=refs,tutors=tutors,notes=notes)

@app.post('/users/create')
@roles('coordinacion')
def create_user():
 role=request.form.get('role'); email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
 if role not in ('estudiante','tutor','coordinacion') or len(password)<10 or not email or User.query.filter_by(email=email).first(): flash('Revisa rol, correo y contraseña (mínimo 10 caracteres).','error'); return redirect(url_for('home'))
 tutor_id=int(request.form['tutor_id']) if role=='estudiante' and request.form.get('tutor_id') else None
 if tutor_id and not User.query.filter_by(id=tutor_id,role='tutor').first(): abort(400)
 db.session.add(User(name=request.form['name'].strip(),email=email,numero_control=numero_control,password=generate_password_hash(password),role=role,career=request.form.get('career',''),semester=int(request.form['semester']) if request.form.get('semester') else None,tutor_id=tutor_id)); db.session.commit(); flash('Cuenta creada.'); return redirect(url_for('home'))
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
