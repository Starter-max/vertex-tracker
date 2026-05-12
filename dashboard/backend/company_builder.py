from pathlib import Path
from datetime import datetime
import json, re
import redis.asyncio as aioredis

BASE = Path(__file__).resolve().parents[2]
PROJECTS_DIR = BASE / 'projects'
PROJECT_COMPANY_PATTERNS = ['создай компанию','набери команду','создай агентов','собери проект','хочу разработать проект','хочу разработать','пусть агенты сделают','нужна команда разработки','создай проектную компанию','подключи сотрудников','добавь скиллы','пробрось в dashboard','собери команду','создай проект','начни разработку','покажи чат агентов','покажи команду','что агенты решили','покажи решения','запусти следующий цикл','пауза','паузу','поставь на паузу','удали компанию','удали проект']
ROLE_LIBRARY = [
 ('project-director','Project Director','достижение результата, координация команды, сроки'),('product-architect','Product Architect','смысл продукта, требования, сценарии, MVP'),('system-architect','System Architect','архитектура, зависимости, интеграции'),('tech-lead','Tech Lead','технические решения, декомпозиция разработки'),('backend-developer','Developer Backend','backend, API, база, интеграции'),('frontend-developer','Developer Frontend','dashboard, UX, интерфейс'),('qa-auditor','QA Auditor','тесты, регрессии, критерии качества'),('security-reviewer','Security Reviewer','секреты, доступы, безопасность'),('documentation-writer','Documentation Writer','документация, changelog, owner summary'),('cost-controller','Cost Controller','бюджет, лимиты, расходы'),('risk-manager','Risk Manager','риски, блокеры, эскалация')]

def is_project_company_request(text: str) -> bool:
    t=(text or '').lower(); return any(p in t for p in PROJECT_COMPANY_PATTERNS) or bool(re.search(r'/(чат|решения|споры|команда|запусти|пауза)\s+', t))

def slugify(name: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ]+','-', name.strip().lower()).strip('-')
    tr={'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch','ы':'y','э':'e','ю':'yu','я':'ya','ь':'','ъ':''}
    s=''.join(tr.get(ch,ch) for ch in s); s=re.sub(r'[^a-z0-9-]+','',s).strip('-'); return s or 'project'

def classify_project(text: str) -> str:
    t=(text or '').lower()
    if 'dashboard' in t or 'дашборд' in t: return 'dashboard_module'
    if 'seo' in t or 'контент' in t: return 'content_seo_project'
    if 'исслед' in t or 'research' in t: return 'research_project'
    if 'инфра' in t or 'redis' in t or 'postgres' in t: return 'infrastructure_project'
    if 'ассист' in t or 'личн' in t: return 'personal_assistant'
    return 'software_product'

def extract_project_name(text: str) -> str:
    t=(text or '').strip(); m=re.search(r'(?:проект(?:а|у)?|под|для)\s+([A-Za-zА-Яа-яЁё0-9 _-]{3,60})', t, re.I)
    if m: return m.group(1).strip(' ."')
    if 'p_test' in t.lower() or 'тест' in t.lower(): return 'Test Agent Company'
    return 'Agent Company Project'

def select_roles(ptype):
    base=['project-director','product-architect','system-architect','tech-lead','qa-auditor','documentation-writer','cost-controller','risk-manager']
    if ptype in ('software_product','dashboard_module','internal_tool'): base += ['backend-developer','frontend-developer','security-reviewer']
    return [r for r in ROLE_LIBRARY if r[0] in base]

def write(path: Path, content: str): path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding='utf-8')
def project_path(pid, slug): return PROJECTS_DIR / f'{pid.lower()}-{slug}'

def agent_msg(aid, role, pid, task, pos, why, risks, need, prop):
    return f"[AGENT]\nИмя: {aid}\nРоль: {role}\nПроект: {pid}\nЗадача: {task}\n\n[ПОЗИЦИЯ]\n{pos}\n\n[ОБОСНОВАНИЕ]\n{why}\n\n[РИСКИ]\n{risks}\n\n[НУЖНО ОТ ДРУГИХ]\n{need}\n\n[РЕШЕНИЕ/ПРЕДЛОЖЕНИЕ]\n{prop}\n"

async def create_project_company(pool, redis_url: str, owner_text: str, source='owner', forced_pid=None):
    name='Test Agent Company' if forced_pid=='P_TEST' else extract_project_name(owner_text); ptype=classify_project(owner_text); pid=forced_pid or ('p'+datetime.now().strftime('%m%d%H%M')); slug=slugify(name); pdir=project_path(pid, slug); roles=select_roles(ptype); now=datetime.now().astimezone().isoformat()
    for d in ['company/agents','workroom/messages','workroom/decisions','workroom/debates','workroom/summaries','kanban','docs','outputs/reports','outputs/artifacts','outputs/releases']: (pdir/d).mkdir(parents=True, exist_ok=True)
    write(pdir/'project.json', json.dumps({'project_id':pid,'name':name,'type':ptype,'status':'PLANNING','owner':'CEO','created_at':now,'source_text':owner_text,'path':str(pdir)}, ensure_ascii=False, indent=2))
    write(pdir/'README.md', f'# {name}\n\nПроектная агентная компания создана A09 Company Builder.\nProject ID: {pid}\nStatus: PLANNING\n')
    write(pdir/'company/company-charter.md', f'# Устав проектной компании {name}\n\nМиссия: создать рабочий результат по запросу владельца без ручного выбора ролей и досок.\n\nЗачем владельцу: снизить операционную нагрузку и экранное время владельца.\n\nГраницы: проектирование, планирование, безопасная разработка, канбан, документация, workroom и эскалации.\n\nУспех: есть структура, команда, канбан, workroom, первые решения и следующий шаг.\n\nСпрашивать владельца: удаление, секреты, внешний доступ, бюджет > $2, production-изменения, массовые изменения БД.\n')
    write(pdir/'company/org-structure.md', '# Org Structure\n\n'+'\n'.join([f'- {role}: {resp}' for _,role,resp in roles]))
    write(pdir/'company/agents.md', '# Agents\n\n'+'\n'.join([f'- {pid.lower()}-{rid}: {role}' for rid,role,_ in roles]))
    write(pdir/'company/skills.md', '# Skills Map\n\nГотовые skills: company-builder, master-router, kanban-aggregator.\nНужные skills: project-specific architecture, dashboard workroom integration, QA checklist.\n')
    write(pdir/'company/communication-rules.md', '# Communication Rules\n\nАгенты пишут структурированные сообщения в workroom/messages/YYYY-MM-DD.md. Решения — decisions. Споры — debates.\n')
    write(pdir/'company/escalation-rules.md', '# Escalation Rules\n\nЭскалировать владельцу: удаление, секреты, внешний доступ, budget > $2, production, массовые изменения БД.\n')
    tasks=['Уточнить требования','Зафиксировать устав проекта','Сформировать команду','Проверить окружение','Спроектировать архитектуру','Составить MVP-план','Реализовать MVP','Проверить качество','Проверить безопасность','Подготовить документацию','Подключить dashboard Agent Workroom','Подготовить итог владельцу']
    write(pdir/'kanban/initial-plan.md', '# Initial Kanban\n\n'+'\n'.join([f'{i+1}. {t}' for i,t in enumerate(tasks)]))
    for doc in ['requirements','architecture','risks','testing','operations']: write(pdir/f'docs/{doc}.md', f'# {doc.title()}\n\nСоздано A09. Заполняется проектной командой.\n')
    for rid,role,resp in roles:
        aid=f'{pid.lower()}-{rid}'; write(pdir/f'company/agents/{aid}.md', f'# {aid}\n\nРоль: {role}\nЦель: {resp}.\nМожет сам: локальные заметки, workroom-сообщения, безопасные kanban-предложения.\nТребует подтверждения: удаление, секреты, внешний доступ, бюджет > $2, production.\nSkills: company-builder, kanban-aggregator, project-specific skills.\nВходы: задачи владельца, канбан, решения workroom.\nВыходы: сообщения, карточки, отчёты, решения.\nЭскалация: через Project Director и Risk Manager.\n')
    async with pool.acquire() as c:
        await c.execute("INSERT INTO projects(id,name,type,status,budget_daily,budget_monthly) VALUES($1,$2,$3,'active',2.00,40.00) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,type=EXCLUDED.type,status='active'", pid.lower(), name, ptype[:20])
        for rid,role,resp in roles:
            aid=f'{pid.lower()}-{rid}'; await c.execute("INSERT INTO agents(id,project_id,name,role,status) VALUES($1,$2,$3,$4,'configured') ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, role=EXCLUDED.role, status='configured'", aid, pid.lower(), role, role[:50])
        for i,t in enumerate(tasks,1):
            cid=f'{pid.lower()}-a09-{i:03d}'; agent=f'{pid.lower()}-project-director' if i<4 else None
            await c.execute("""INSERT INTO kanban_cards(id,title,description,card_type,layer,project_id,agent_id,status,priority,tags,metadata) VALUES($1,$2,$3,'task','operational',$4,$5,$6,$7,$8,$9::jsonb) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title,description=EXCLUDED.description,updated_at=NOW()""", cid,t,f'A09 initial task for {name}',pid.lower(),agent,'in_progress' if i==1 else 'planned','P1' if i<=5 else 'P2',['a09','project-company'],json.dumps({'source':'a09-company-builder'}))
        event_id = f"a09_{pid.lower()}_{int(datetime.now().timestamp())}"
        await c.execute("""INSERT INTO inbox_events(event_id, source, owner_id, raw_text, normalized_intent, intent_class, project_id, risk_level, status, requires_approval, result_summary, agents_used, skills_used, metadata)
                         VALUES($1,$2,'owner',$3,$4,'PROJECT_COMPANY_REQUEST',$5,'low','done',false,$6,$7::jsonb,$8::jsonb,$9::jsonb)""",
                        event_id, source, owner_text, owner_text.lower()[:500], pid.lower(), f'A09 created project company {pid}',
                        json.dumps([f'{pid.lower()}-{rid}' for rid,_,_ in roles]), json.dumps(['company-builder','master-router','kanban-aggregator']), json.dumps({'path': str(pdir)}))
    kickoff=[('project-director','Project Director','цель понятна: создать автономный dashboard-модуль и показать владельцу ход работы','нужен минимальный маршрут от требования к MVP','scope creep','Product Architect: зафиксировать MVP','начинаем PLANNING'),('product-architect','Product Architect','MVP должен показать проект, команду, канбан и сообщения','это закрывает owner-сценарий','фасад без backend-связи','Tech Lead: проверить API','фиксирую требования'),('system-architect','System Architect','PostgreSQL для проекта/агентов/канбана, файлы для workroom','безопасно без risky schema migration','нет dashboard-блока','Frontend: добавить блок или задачу','архитектура MVP принята'),('tech-lead','Tech Lead','сначала endpoints просмотра workroom, затем dashboard','owner увидит коммуникацию','сломать index.html','QA: curl/API','делаем безопасно'),('risk-manager','Risk Manager','не менять .env и не удалять данные','таков мандат A09','массовые UPDATE','Cost Controller: лимит','работаем через upsert'),('cost-controller','Cost Controller','лимит MVP до $2','файлы почти бесплатны','LLM-циклы могут расти','Project Director: ограничить циклы','бюджет активен'),('qa-auditor','QA Auditor','готовность: DB rows, files, messages, decision, APIs','проверяемо curl/SQL/files','dashboard может быть отложен','Documentation Writer: ограничения','критерии QA приняты'),('documentation-writer','Documentation Writer','итог фиксируется в README, decisions, summary','это прозрачно','устаревание docs','все агенты: кратко','создаю summary')]
    date=datetime.now().strftime('%Y-%m-%d'); msgs=[]
    for rid,role,pos,why,risks,need,prop in kickoff:
        aid=f'{pid.lower()}-{rid}'; msgs.append(f'## {now} {aid}\n'+agent_msg(aid,role,pid,'initial kickoff',pos,why,risks,need,prop))
    write(pdir/f'workroom/messages/{date}.md', '\n\n'.join(msgs)+'\n')
    write(pdir/'workroom/summaries/initial-kickoff.md', '# Initial Kickoff\n\nКоманда согласовала PLANNING → BUILDING: требования, архитектура, MVP, QA, dashboard/workroom visibility.\n')
    write(pdir/'workroom/decisions/decision-001-project-start.md', f'# Decision 001: Project Start\n\nПроект {pid} стартует в PLANNING. Минимальный результат: рабочая компания, канбан, workroom и dashboard-задача/блок.\n')
    r=aioredis.from_url(redis_url, decode_responses=True)
    try:
        for stream in ['corp:inbox','corp:tasks','corp:audit','corp:agent_messages']:
            await r.xadd(stream, {'source':'a09-company-builder','project_id':pid.lower(),'event':'project_company_created','message':f'Created {name}','ts':str(datetime.now().timestamp())})
    finally: await r.aclose()
    return {'ok':True,'project_id':pid.lower(),'name':name,'type':ptype,'path':str(pdir),'team':[{'id':f'{pid.lower()}-{rid}','role':role,'responsibility':resp} for rid,role,resp in roles]}

def read_workroom(project_id: str, kind='chat', limit=4000):
    pid=project_id.lower(); matches=list(PROJECTS_DIR.glob(f'{pid}-*'))
    if not matches: return None
    root=matches[0]
    if kind=='team':
        p=root/'company/agents.md'; return p.read_text(encoding='utf-8') if p.exists() else ''
    sub={'chat':'messages','decisions':'decisions','debates':'debates'}.get(kind,'messages'); folder=root/'workroom'/sub
    files=sorted(folder.glob('*.md'), key=lambda p:p.stat().st_mtime, reverse=True); text='\n\n'.join(p.read_text(encoding='utf-8') for p in files[:3])
    return text[-limit:] if text else ''

async def route_project_company(pool, redis_url: str, message: str, source='owner'):
    t=(message or '').lower(); m=re.search(r'(p_test|p\d+)', t); pid=m.group(1).upper() if m else None
    if 'удали' in t or 'delete' in t: return {'ok':False,'intent_class':'PROJECT_COMPANY_REQUEST','status':'waiting_approval','response':'Нужно подтверждение: удаление проектной компании запрещено без явного approval. A — подтвердить, B — отменить, C — архивировать безопасно.'}
    if ('покажи чат' in t or t.startswith('/чат')) and pid: return {'ok':True,'intent_class':'WORKROOM_VIEW','status':'done','response':(read_workroom(pid,'chat') or 'Workroom не найден.')[:2000]}
    if (any(x in t for x in ['решени','решил','решила','решили','решило']) or t.startswith('/решения')) and pid: return {'ok':True,'intent_class':'WORKROOM_DECISIONS','status':'done','response':(read_workroom(pid,'decisions') or 'Решения не найдены.')[:2000]}
    if ('спор' in t or t.startswith('/споры')) and pid: return {'ok':True,'intent_class':'WORKROOM_DEBATES','status':'done','response':(read_workroom(pid,'debates') or 'Активных споров нет.')[:2000]}
    if ('команд' in t or t.startswith('/команда')) and pid: return {'ok':True,'intent_class':'PROJECT_TEAM_VIEW','status':'done','response':(read_workroom(pid,'team') or 'Команда не найдена.')[:2000]}
    if 'пауз' in t and pid:
        async with pool.acquire() as c: await c.execute("UPDATE projects SET status='paused' WHERE id=$1", pid.lower())
        return {'ok':True,'intent_class':'PROJECT_PAUSE','status':'done','response':f'{pid} поставлен на паузу.'}
    if 'запусти' in t and pid:
        matches=list(PROJECTS_DIR.glob(f'{pid.lower()}-*'))
        if matches:
            p=matches[0]/f"workroom/messages/{datetime.now().strftime('%Y-%m-%d')}.md"; p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('a',encoding='utf-8') as f: f.write(f"\n## {datetime.now().astimezone().isoformat()} {pid.lower()}-project-director\nProject Director: запускаю следующий цикл. Следующее: Tech Lead обновляет MVP-план, QA фиксирует проверку.\n")
        return {'ok':True,'intent_class':'PROJECT_CYCLE_RUN','status':'done','response':f'Запустил следующий цикл работы {pid}. Сообщение добавлено в workroom.'}
    forced='P_TEST' if ('p_test' in t or 'тест' in t) else None; result=await create_project_company(pool, redis_url, message, source=source, forced_pid=forced)
    team='\n'.join([f"• {x['role']} — {x['responsibility']}" for x in result['team'][:6]])
    return {'ok':True,'intent_class':'PROJECT_COMPANY_REQUEST','status':'done','project_id':result['project_id'],'data':result,'response':f"Создал проектную компанию для {result['name']}.\n\nКоманда:\n{team}\n\nСоздано: проект в БД, агенты, канбан, workroom, документация, Redis-события.\nПервое решение: старт в PLANNING; цель — MVP + видимость workroom.\nДальше: A — запустить разработку MVP, B — показать состав команды, C — открыть обсуждение агентов."}
