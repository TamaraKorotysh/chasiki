// Собирает все фразы игры «Часики» в блоки для озвучки в ElevenLabs.
const fs = require('fs');
const path = require('path');
const SRC = 'E:/chasiki/index.html';
const OUT = 'E:/chasiki/voice';
fs.mkdirSync(OUT, { recursive: true });
const html = fs.readFileSync(SRC, 'utf8');

const CARD=['ноль','один','два','три','четыре','пять','шесть','семь','восемь','девять','десять','одиннадцать','двенадцать','тринадцать','четырнадцать','пятнадцать','шестнадцать','семнадцать','восемнадцать','девятнадцать'];
const FEM=CARD.slice();FEM[1]='одна';FEM[2]='две';
const TENS={20:'двадцать',30:'тридцать',40:'сорок',50:'пятьдесят',60:'шестьдесят',70:'семьдесят',80:'восемьдесят',90:'девяносто'};
const ORD_GEN=['','первого','второго','третьего','четвёртого','пятого','шестого','седьмого','восьмого','девятого','десятого','одиннадцатого','двенадцатого'];
const HOUR_NOM=['','час','два','три','четыре','пять','шесть','семь','восемь','девять','десять','одиннадцать','двенадцать'];
const GEN=['','одной','двух','трёх','четырёх','пяти','шести','семи','восьми','девяти','десяти','одиннадцати','двенадцати','тринадцати','четырнадцати','пятнадцати','шестнадцати','семнадцати','восемнадцати','девятнадцати','двадцати'];
function plural(n,a,b,c){const t=n%100,u=n%10;if(t>10&&t<20)return c;if(u===1)return a;if(u>=2&&u<=4)return b;return c}
function numF(n){if(n<20)return FEM[n];if(n>=100)return 'сто'+(n>100?' '+numF(n-100):'');const t=Math.floor(n/10)*10,u=n%10;return TENS[t]+(u?' '+FEM[u]:'')}
function minPhrase(m){return numF(m)+' '+plural(m,'минута','минуты','минут')}
function hourPhrase(h){return h===1?'час':CARD[h]+' '+plural(h,'час','часа','часов')}
function genN(n){return n<=20?GEN[n]:'двадцати '+GEN[n-20]}
function timeWords(h,m){
  const nx=h%12+1;
  if(m===0)return 'ровно '+hourPhrase(h);
  if(m===30)return 'половина '+ORD_GEN[nx];
  if(m===15)return 'четверть '+ORD_GEN[nx];
  if(m<35)return minPhrase(m)+' '+ORD_GEN[nx];
  const r=60-m;let bez;
  if(r===15)bez='без четверти';else if(r%5===0)bez='без '+genN(r);
  else bez='без '+genN(r)+' '+(r%10===1&&r!==11?'минуты':'минут');
  return bez+' '+HOUR_NOM[nx];
}
const cap=s=>s[0].toUpperCase()+s.slice(1);
const INSTR=['','часом','двумя','тремя','четырьмя','пятью','шестью','семью','восемью','девятью','десятью','одиннадцатью','двенадцатью'];
const numM=n=>n<20?CARD[n]:'двадцать'+(n>20?' '+CARD[n-20]:'');
const h24W=(h,m)=>m===0?numM(h)+' '+plural(h,'час','часа','часов'):numM(h)+' '+numF(m);
const perG=h=>h<5?'ночи':h<12?'утра':h<17?'дня':'вечера';
const timeWordsRaw=(h,m)=>timeWords(h,m);
const clean=s=>s.replace(/\p{Extended_Pictographic}|\uFE0F|\u200D/gu,'').replace(/\s+/g,' ').replace(/\s([.,!?])/g,'$1').trim();

// ---------- блоки ----------
const blocks=[]; // {id,title,tag,note,items:[{id,text}]}
function block(id,title,tag,items,note=''){blocks.push({id,title,tag,note,items})}

// 1. Объяснения уроков — тексты берём прямо из игры
const lessonRe=/\{id:'(L\w+)',em:'[^']*',title:'([^']+)'[\s\S]*?(?=\{id:'L\w+',em|\];\s*const EXTRAS)/g;
const dig=t=>t.replace(/(\d{1,2}):(\d\d)/g,(_,h,m)=>{h=+h;m=+m;return (h===0?'ноль-ноль':h<20?CARD[h]:numF(h).replace('одна','один').replace('две','два'))+' '+(m===0?'ноль-ноль':m<10?'ноль '+CARD[m]:numF(m))});
let lessonNo=0;
let lm;
while((lm=lessonRe.exec(html))){
  const L=lm[1];const body=lm[0];lessonNo++;
  const steps=[...body.matchAll(/\{t:'([^']+)'/g)].map(x=>x[1]);
  block('intro-'+L,'Урок '+lessonNo+' «'+lm[2]+'»: объяснение будильника','[warmly]',
    steps.map((t,i)=>({id:`intro.${L}.${i+1}`,text:clean(dig(t))})),
    'Длинные фразы. Тёплый рассказ ребёнку, с улыбкой, не торопясь.');
}

// 2. Похвала и реакции
const praise=['Молодец!','Правильно!','Отлично!','Здорово!','Умница!','Верно!','Так держать!','Получилось!','Ура!'];
block('praise','Похвала','[excited]',praise.map((t,i)=>({id:'praise.'+(i+1),text:t})),'Радостно, искренне, коротко.');

// 3. Вопросы и связки (к ним потом приклеивается время или цифра)
const glue=[
 ['q.where','Где…'],['q.set','Поставь…'],['q.look_where','Смотри, вот где…'],['q.look_so','Смотри, вот так:'],
 ['q.right_so','Правильно так:'],['q.now','Сейчас…'],['q.passed','Прошло…'],
 ['q.find_num','Найди цифру…'],['q.this_num','Это цифра…'],['q.seek_num','Ищи цифру…'],
 ['per.morning','…утро.'],['per.day','…день.'],['per.evening','…вечер.'],['per.night','…ночь.'],
];
block('glue','Связки (начало и конец составных фраз)','',glue.map(([id,text])=>({id,text})),
 'Это кусочки, к которым игра приклеит время или цифру. Произносить так, будто фраза продолжается: «Где…» — с вопросительным подъёмом, «Поставь…» — с лёгкой паузой в конце.');

// 4. Фразы игр
const games=[
 ['g.again','Посмотри ещё раз.'],['g.notquite','Не совсем. Посмотри ещё раз.'],
 ['g.order_start','Нажимай на цифры по порядку: один, два, три…'],['g.order_first','Начни с цифры один.'],
 ['g.order_done','Ура! Все цифры по порядку!'],
 ['g.read_q','Который час? Как это записать цифрами?'],
 ['g.day_q','Посмотри на часы. Что мы делаем в это время?'],['g.day_no','Нет. Посмотри на часы ещё раз.'],
 ['g.jump_q','Нажми «Старт» и прыгай, пока зелёная стрелка-мышка не пробежит целый круг!'],
 ['g.jump_go','Прыгай!'],['g.jump_half','Половина минуты! Прыгай дальше!'],
 ['g.jump_done','Ура! Прошла целая минута! Посмотри: длинная стрелка сделала один шажок.'],
 ['g.guess_q','Нажми «Старт», закрой глаза и считай про себя. Когда покажется, что прошла минута, нажми «Стоп».'],
 ['g.guess_exact','Почти точно! Ты чувствуешь минуту!'],['g.guess_close','Совсем рядом с минутой!'],
 ['g.guess_short','Минута ещё не закончилась — она длиннее.'],['g.guess_long','Минута уже прошла — она короче.'],
 ['g.task_done','Получилось! Нажми «Дальше».'],
 ['r.3','Великолепно!'],['r.2','Хорошо! Можно ещё лучше.'],['r.1','Ты молодец, что старался! Давай ещё раз.'],
 ['r.new','Открыт новый урок!'],
 ['lock.lesson','Этот урок откроется, когда пройдёшь предыдущий.'],['lock.day','Эта игра откроется после третьего урока.'],
 ['ui.voice_on','Голос включён.'],
];
block('games','Фразы игр','[cheerfully]',games.map(([id,text])=>({id,text})),'Бодро и понятно, как ведущая детской игры.');

// 5. «Мой день»
const day=[['day.7m','Семь часов утра — просыпаемся!'],['day.8m','Восемь часов утра — завтракаем!'],['day.9m','Девять часов утра — идём в садик!'],
 ['day.1d','Час дня — обедаем!'],['day.4d','Четыре часа дня — полдник!'],['day.530e','Половина шестого вечера — гуляем!'],
 ['day.7e','Семь часов вечера — ужинаем!'],['day.9e','Девять часов вечера — ложимся спать!']];
block('day','Игра «Мой день»','[cheerfully]',day.map(([id,text])=>({id,text})));

// 6. Подсказки
const hints=[['h.hour','Короткая стрелка должна смотреть на цифру…'],['h.minute','Длинная стрелка должна смотреть…'],
 ['h.min_top','…наверх, на двенадцать.'],['h.on_num','…на цифру…'],
 ['h.tick1','…на первую чёрточку после цифры…'],['h.tick2','…на вторую чёрточку после цифры…'],
 ['h.tick3','…на третью чёрточку после цифры…'],['h.tick4','…на четвёртую чёрточку после цифры…'],
 ['h.hour_on','Длинная — верно! Теперь короткая: она должна смотреть на цифру…'],
 ['h.hour_between','Длинная — верно! А короткая должна стоять…']];
for(let h=1;h<=12;h++)hints.push(['h.btw.'+h,`…между ${INSTR[h]} и ${INSTR[h%12+1]}.`]);
block('hints','Подсказки при ошибке','[gently]',hints.map(([id,text])=>({id,text})),'Мягко, ободряюще. Многоточие означает, что к фразе приклеится продолжение.');

// 7. Числа
const nums=[];for(let n=1;n<=12;n++)nums.push(['n.'+n,cap(CARD[n])+'.']);
for(let n=15;n<=60;n+=5)nums.push(['n.'+n,cap(n<20?CARD[n]:TENS[n]||numF(n))+'.']);
block('numbers','Числа: цифры на часах и счёт пятёрками','',nums.map(([id,text])=>({id,text})),'Чётко, каждое число отдельно, с точкой.');

// 8. Секунды для игры «Угадай минуту»
for(let a=1;a<=119;a+=20){const it=[];for(let s=a;s<Math.min(a+20,120);s++)it.push({id:'sec.'+s,text:cap(numF(s)+' '+plural(s,'секунда','секунды','секунд'))+'.'});
  block(`sec-${a}`,`Секунды ${a}–${Math.min(a+19,119)}`,'',it,'Ровно, спокойно, одинаковой интонацией.')}

// 8b. Объяснения времени (склеиваются из кусочков)
const ORD_NOM=['','первый','второй','третий','четвёртый','пятый','шестой','седьмой','восьмой','девятый','десятый','одиннадцатый','двенадцатый'];
const GENH=['','часа','двух часов','трёх часов','четырёх часов','пяти часов','шести часов','семи часов','восьми часов','девяти часов','десяти часов','одиннадцати часов','двенадцати часов'];
const passed=h=>h===1?'один час уже прошёл':hourPhrase(h)+' уже прошло';
const betw=h=>'между '+INSTR[h]+' и '+INSTR[h%12+1];
{const it=[];
 for(let h=1;h<=12;h++)it.push({id:'ex.passed.'+h,text:cap(passed(h))+',…'});
 for(let n=1;n<=12;n++)it.push({id:'ex.going.'+n,text:'…идёт '+ORD_NOM[n]+' час…'});
 it.push({id:'ex.half',text:'…и от него прошла половина — тридцать минут.'},{id:'ex.quarter',text:'…и от него прошла четверть — пятнадцать минут.'},
         {id:'ex.passed_n',text:'…и от него прошло…'},{id:'ex.passed_f',text:'…и от него прошла…'});
 block('explain-1','Объяснения: «сколько прошло, какой час идёт»','[warmly]',it,'Кусочки объяснения вида «Два часа уже прошло, — идёт третий час, — и от него прошло — пятнадцать минут». Читать спокойно, объясняюще.');
 const it2=[];
 for(let n=1;n<=12;n++)it2.push({id:'ex.left.'+n,text:'…До '+GENH[n]+' осталось…'},{id:'ex.leftf.'+n,text:'…До '+GENH[n]+' осталась…'});
 for(let n=1;n<=12;n++)it2.push({id:'ex.leftq.'+n,text:'…До '+GENH[n]+' осталась четверть часа — пятнадцать минут.'});
 block('explain-2','Объяснения: «сколько осталось до следующего часа»','[warmly]',it2);
 const it3=[];for(let h=1;h<=12;h++)it3.push({id:'ex.whole.'+h,text:'Длинная стрелка наверху — значит, ровно. Короткая на цифре '+CARD[h]+' — '+hourPhrase(h)+'.'});
 block('explain-3','Объяснения: ровное время','[warmly]',it3);
 for(let a=1;a<=34;a+=17){const it4=[];for(let m=a;m<Math.min(a+17,35);m++)it4.push({id:'min.'+m,text:'…'+minPhrase(m)+'.'});
   block('minutes-'+a,'Минуты '+a+'–'+Math.min(a+16,34)+' (конец объяснения)','',it4,'Окончания фраз «…и от него прошло — пятнадцать минут». Ровно, с точкой в конце.')}
}
// 8c. Какой час идёт
{const it=[{id:'wh.q',text:'Какой час идёт? Посмотри, между какими цифрами стоит короткая стрелка.'}];
 for(let h=1;h<=12;h++)it.push({id:'wh.btw.'+h,text:'…короткая стрелка '+betw(h)+'.'});
 for(let n=1;n<=12;n++)it.push({id:'wh.so.'+n,text:'Значит, идёт '+ORD_NOM[n]+' час.'});
 block('which-1','Игра «Какой час идёт?»: объяснение','[warmly]',it);
 const it2=[];
 for(let h=1;h<=12;h++)it2.push({id:'wh.past.'+h,text:'Цифру '+CARD[h]+' стрелка уже прошла — этот час закончился. Какой час идёт сейчас?'});
 for(let h=1;h<=12;h++)it2.push({id:'wh.notyet.'+h,text:'До цифры '+CARD[h]+' стрелка ещё не дошла. Посмотри внимательнее.'});
 block('which-2','Игра «Какой час идёт?»: подсказки','[gently]',it2);
 const it3=[];
 for(let n=2;n<=12;n++)it3.push({id:'hs.q.'+n,text:'Поставь короткую стрелку так, чтобы шёл '+ORD_NOM[n]+' час.'});
 for(let n=1;n<=12;n++){const p=n-1||12;it3.push({id:'hs.why.'+n,text:cap(ORD_NOM[n])+' час идёт, когда '+passed(p)+': короткая стрелка '+betw(p)+'.'})}
 block('hourshow-1','Игра «Покажи нужный час»','[warmly]',it3);
 const it4=[];for(let h=1;h<=12;h++)it4.push({id:'hs.edge.'+h,text:'Стрелка стоит прямо на цифре '+CARD[h]+' — это ровно '+hourPhrase(h)+', новый час только начинается. Сдвинь её чуть дальше.'});
 block('hourshow-2','Игра «Покажи нужный час»: подсказки','[gently]',it4);
}
// 8d. Подсказки «Поставь стрелки»
{const it=[];
 for(let h=1;h<=12;h++)it.push({id:'sh.hour.'+h,text:'Длинная — верно! Теперь короткая: она должна смотреть на цифру '+CARD[h]+'.'});
 for(let h=1;h<=12;h++)it.push({id:'sh.btw.'+h,text:'Длинная — верно! А короткая должна стоять '+betw(h)+': '+passed(h)+', идёт '+ORD_NOM[h%12+1]+' час.'});
 block('showhint-1','Подсказки «Поставь стрелки»: короткая стрелка','[gently]',it);
 const it2=[];for(let k=1;k<=11;k++)it2.push({id:'sh.div.'+k,text:'Минут '+numF(k*5)+'. Раздели на пять: получится '+CARD[k]+'. Длинная стрелка должна смотреть на цифру '+CARD[k]+'.'});
 it2.push({id:'sh.digq',text:'Поставь стрелки на время, которое написано цифрами.'},{id:'fd.digq',text:'Найди часы, на которых такое время.'});
 block('showhint-2','Урок «Цифры в стрелки»: подсказки','[gently]',it2);
}
// 8e. 24 часа
{const it=[];for(let h=0;h<24;h++)for(const m of [0,30])it.push({id:`h24.${h}.${m}`,text:cap(h24W(h,m))+'.'});
 for(let a=0;a<48;a+=24)block('h24-'+(a/24+1),'24 часа: '+(a?'12:00 – 23:30':'0:00 – 11:30'),'',it.slice(a,a+24),'Как диктор: «пятнадцать часов», «двадцать два тридцать». Ровно.');
 const it2=[{id:'c24.q',text:'Как сказать по-другому?'},{id:'c24.is',text:'…это…'},{id:'c24.tip13',text:'Подсказка: отними двенадцать.'},{id:'c24.tip0',text:'Подсказка: до полудня ничего не отнимаем.'},
   {id:'r24.q',text:'Что сейчас показывает телефон?'},{id:'r24.tip',text:'Посмотри, какое сейчас время суток: утро, день или вечер?'},{id:'s24.minus',text:'Отними двенадцать:'},{id:'g.look',text:'Смотри.'}];
 for(let h=0;h<24;h++){const hh=h%12||12;it2.push({id:'lab.'+h,text:'…'+hourPhrase(hh)+' '+perG(h)+'.'})}
 block('h24-talk','24 часа: вопросы и ответы','[cheerfully]',it2);
 const it3=[];for(let h=0;h<24;h++)it3.push({id:'r24.why.'+h,text:h===12?'Сейчас полдень — двенадцать часов дня, двенадцать ноль-ноль. С него начинается второй круг.':h>12?'Сейчас '+(h<17?'день':'вечер')+' — второй круг, прибавляем двенадцать: '+CARD[h-12]+' плюс двенадцать — '+numM(h)+'.':'Сейчас '+(h<5?'ночь':'утро')+' — первый круг, ничего не прибавляем.'});
 block('h24-why','24 часа: объяснения «что на телефоне»','[warmly]',it3);
 const it4=[];for(let h=13;h<24;h++)for(const m of [0,30]){const w=m?timeWordsRaw(h-12,30):hourPhrase(h-12);
   it4.push({id:`s24.why.${h}.${m}`,text:cap(numM(h))+' минус двенадцать — '+CARD[h-12]+'. Значит, '+w+' '+perG(h)+'.'})}
 block('h24-show','24 часа: объяснения «поставь стрелки»','[warmly]',it4);
}

// 9. Время: 720 фраз
const hours=[12,1,2,3,4,5,6,7,8,9,10,11];
for(const h of hours){for(const part of [0,1,2]){const it=[];
  for(let m=part*20;m<part*20+20;m++)it.push({id:`t.${String(h%12).padStart(2,'0')}${String(m).padStart(2,'0')}`,text:cap(timeWords(h,m))+'.'});
  const hh=String(h).padStart(2,'0');
  block(`time-${hh}-${part+1}`,`Время ${h}:${String(part*20).padStart(2,'0')} – ${h}:${String(part*20+19).padStart(2,'0')}`,'',it,'Спокойно и ясно, как будто отвечаешь «который час». Все фразы одинаковой интонацией.')}}

// ---------- запись ----------
const SEP='\n\n[long pause]\n\n';
let md='';let total=0,chars=0;
blocks.forEach((b,i)=>{
  const n=String(i+1).padStart(3,'0');b.file=`${n}_${b.id}.mp3`;
  const text=b.items.map(x=>(b.tag?b.tag+' ':'')+x.text).join(SEP);
  total+=b.items.length;chars+=text.length;
  md+=`\n---\n\n### Блок ${n} · ${b.title}\n\nФайл: **${b.file}** · фраз: ${b.items.length}${b.note?'  \n'+b.note:''}\n\n\`\`\`text\n${text}\n\`\`\`\n`;
});
const head=fs.readFileSync(path.join(__dirname,'head.md'),'utf8');
const toc=blocks.map(b=>`- **${b.file.slice(0,3)}** · ${b.title} (${b.items.length})`).join(String.fromCharCode(10));
const ex=blocks.find(b=>b.id.startsWith('time-')).file;
fs.writeFileSync(path.join(OUT,'ОЗВУЧКА.md'),head.replace('{BLOCKS}',blocks.length).replace('{PHRASES}',total).replace('{CHARS}',(Math.round(chars/1000)*1000).toLocaleString('ru-RU')).replace('{EXAMPLE}',ex).replace('{TOC}',toc)+md);
// чистый txt: только то, что читается вслух, все фразы подряд через [long pause]
const txt=blocks.map(b=>b.items.map(x=>(b.tag?b.tag+' ':'')+x.text).join(SEP)).join(SEP)+'\n';
fs.writeFileSync(path.join(OUT,'ОЗВУЧКА.txt'),txt.replace(/\n/g,'\r\n'));
fs.writeFileSync(path.join(OUT,'phrases.json'),JSON.stringify(blocks.map(b=>({file:b.file,items:b.items})),null,1));
console.log('blocks',blocks.length,'phrases',total,'chars',chars);
