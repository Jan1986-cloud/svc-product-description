// RoboServe Wait Quotes — herbruikbaar wachtcomponent
// Gebruik: rsWait.start('containerId', 'product-description') / rsWait.stop()
var rsWait=(function(){
var generic=[
"Instant wonderen toveren duurt iets langer.",
"Rome is ook niet in één API-call gebouwd.",
"Onze AI drinkt even een kop koffie. Figuurlijk dan.",
"De beste dingen in het leven zijn het wachten waard.",
"We poetsen uw resultaat nog even op.",
"Achter de schermen wordt hard gewerkt. Echt waar.",
"Even geduld, perfectie heeft tijd nodig.",
"We checken nog even de spelling. En de grammatica. En de stijl.",
"Uw geduld wordt beloond met kwaliteit.",
"De AI denkt na. Dat is een goed teken.",
"Bijna klaar... zei de AI optimistisch.",
"We tellen de woorden. En dan nog een keer.",
"De pixels worden zorgvuldig gerangschikt.",
"Kwaliteit boven snelheid, altijd.",
"De hamsters in onze servers draaien op volle toeren.",
"We verzamelen de beste woorden uit het hele internet.",
"Nog even en u heeft iets om trots op te zijn.",
"De AI is enthousiast over uw opdracht.",
"We doen het in één keer goed. Vandaar het wachten.",
"Achter elke goede tekst zit een denkend algoritme.",
"De AI bladert door haar woordenboek.",
"Uw resultaat wordt met liefde samengesteld.",
"We fine-tunen de laatste details.",
"Niet alle helden dragen capes. Sommige genereren tekst.",
"De AI heeft zoveel ideeën, moeilijk kiezen.",
"We controleren of alles klopt. Dubbel.",
"Het creatieve proces is in volle gang.",
"Uw opdracht is in goede handen. Digitale handen, maar toch.",
"De AI heeft er zin in. Dat scheelt.",
"We schaven nog even aan de randjes.",
"Geduld is een schone zaak. En gratis.",
"De neurale netwerken gloeien.",
"We zoeken de perfecte woorden. Er zijn er 170.000 in het Nederlands.",
"De AI leest uw opdracht voor de derde keer. Grondig.",
"Bijna... nog even de puntjes op de i.",
"We optimaliseren tot het niet beter kan.",
"De servers draaien warm. Letterlijk.",
"Uw content wordt ambachtelijk vervaardigd.",
"De AI heeft een ingeving. Moment.",
"We checken de kwaliteit. En dan nog een keer.",
"Het wachten is bijna voorbij. Bijna.",
"De AI zoekt naar dat ene perfecte woord.",
"We polieren uw resultaat tot het glimt.",
"Creativiteit laat zich niet opjagen.",
"De AI consulteert haar innerlijke copywriter.",
"Nog een paar seconden geniaal nadenken.",
"We wegen elk woord op een goudschaaltje.",
"De AI is in de zone. Niet storen.",
"Uw tekst krijgt de VIP-behandeling.",
"We mengen ingrediënten: data, creativiteit, en een snufje magie.",
"De AI scrolt door haar inspiratiemap.",
"Koffie is gezet, ideeën komen eraan.",
"We vouwen uw tekst als origami: precies en mooi.",
"De AI fluit een deuntje terwijl ze werkt.",
"Nog even, dan heeft u iets bijzonders.",
"We sorteren de woorden op overtuigingskracht.",
"De AI checkt de concurrentie. U wint.",
"Uw opdracht inspireert ons algoritme.",
"We bakken uw tekst goudbruin.",
"De AI tekent een mindmap. Digitaal, uiteraard.",
"Elk goed verhaal heeft een opbouw. We zijn bij het hoogtepunt.",
"We persen het beste uit elke zin.",
"De AI heeft drie concepten. Ze kiest de beste.",
"Uw resultaat wordt samengesteld door 175 miljard parameters.",
"We leggen de laatste hand aan uw meesterwerk.",
"De AI is perfectionistisch. Net als u, waarschijnlijk.",
"Nog een rondje kwaliteitscontrole.",
"We voegen de geheime saus toe.",
"De AI overweegt haar woordkeuze. Zorgvuldig.",
"Bijna klaar. De spanning is om te snijden.",
"We testen uw tekst op wow-factor.",
"De AI heeft goesting in deze opdracht.",
"Uw content marineert in creativiteit.",
"We draaien aan de laatste knoppen.",
"De AI raadpleegt haar stijlgids.",
"Nog even polijsten en dan is het een pareltje.",
"We checken de SEO-waarde. Ziet er goed uit.",
"De AI telt de overtuigingskracht per alinea.",
"Uw tekst is bijna publicatiewaardig.",
"We voegen nog wat schwung toe.",
"De AI is 97% klaar. De laatste 3% is het moeilijkst.",
"Uw resultaat wordt geboren. Het is een mooie tekst.",
"We vergelijken met 10.000 alternatieven. Deze wint.",
"De AI knikt tevreden. Goed teken.",
"Nog een fractie van een eeuwigheid.",
"We doen de finishing touch.",
"De AI heeft haar beste werk geleverd. Bijna.",
"Uw geduld is goud waard. Net als deze tekst.",
"We lezen het nog één keer hardop voor.",
"De AI geeft zichzelf een 9. We gaan voor de 10.",
"Klaar... nee, wacht. Nog iets verbeteren.",
"We zorgen dat elk woord zijn plek verdient.",
"De AI doet haar overwinningsdansje. Bijna klaar.",
"Uw tekst is door de kwaliteitscontrole. Laatste check.",
"We serveren het resultaat op een zilveren dienblad.",
"De AI is trots op wat ze heeft gemaakt.",
"Het aftellen is begonnen.",
"We plakken het laatste stukje van de puzzel.",
"De AI fluistert: dit wordt goed.",
"Nog heel even. Beloofd."
];
var serviceQuotes={
'product-description':[
"We analyseren uw productkenmerken één voor één.",
"De AI bedenkt waarom klanten dit product MOETEN hebben.",
"SEO-magic in de maak. Google gaat dit leuk vinden.",
"We schrijven een beschrijving die verkoopt, niet alleen beschrijft.",
"De AI kruipt in de huid van uw doelgroep.",
"Uw product verdient de beste woorden. Die zoeken we nu.",
"We optimaliseren voor zoekmachines én voor mensen.",
"De AI test of de beschrijving overtuigend genoeg is.",
"We vlechten uw USP's door de tekst.",
"Uw SEO-titel wordt een klikmagneet."
],
'blog-ideas':[
"We brainstormen over onderwerpen die uw doelgroep raken.",
"De AI bedenkt titels waar lezers op klikken.",
"We zoeken de gaten in uw content strategie.",
"Elk idee krijgt een unieke afbeelding. Dat duurt even.",
"De AI analyseert trending topics in uw niche.",
"We genereren afbeeldingen die passen bij uw branding.",
"Uw blog kalender wordt net een stukje voller.",
"De AI combineert creativiteit met zoekvolume.",
"We matchen kleuren met uw website. Pixel-perfect.",
"Elke afbeelding wordt op maat gemaakt. Geen stockfoto's hier."
]
};
var _timer=null;
var _idx=0;
var _pool=[];
function shuffle(a){for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=a[i];a[i]=a[j];a[j]=t;}return a;}
function start(containerId,serviceKey){
stop();
var extra=serviceQuotes[serviceKey]||[];
_pool=shuffle(generic.concat(extra));
_idx=0;
var el=document.getElementById(containerId);
if(!el)return;
el.style.display='block';
show(el);
_timer=setInterval(function(){show(el);},4000);
}
function show(el){
if(_idx>=_pool.length){_idx=0;_pool=shuffle(_pool);}
var q=_pool[_idx++];
var p=el.querySelector('.rs-wait-text');
if(p){p.style.opacity='0';setTimeout(function(){p.textContent=q;p.style.opacity='1';},300);}
}
function stop(){
if(_timer){clearInterval(_timer);_timer=null;}
_idx=0;
}
return{start:start,stop:stop};
})();
