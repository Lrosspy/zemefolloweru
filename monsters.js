/* Databáze příšer – Planeta followerů
   Každá příšera = jeden záznam. Novou přidáš tak, že zkopíruješ záznam, změníš id a hodnoty.
   Kde se příšera objeví, se zapisuje v seznamu SPAWNS v dungeon.html (např. {m:'skeleton',x:-3,z:-12}).

   Pole:
   name      jméno (ukáže se v hláškách)
   hp        životy
   dmg       poškození jednoho úderu
   speed     rychlost při honění hráče (m/s), walk = rychlost při hlídkování
   aggro     na kolik metrů si hráče všimne, leash = jak daleko od svého místa ho pronásleduje
   range     vzdálenost, ze které začne útok, reach = dosah úderu (hráč dál = netrefí)
   windup    za kolik sekund od začátku útoku přijde úder (čas na zablokování), atkDur = délka celého útoku
   cooldown  pauza mezi útoky (s)
   respawn   za kolik sekund se po smrti znovu objeví
   scale     velikost (1 = jako hráč)
   look      vzhled: color = barva těla, eyes = barva očí, ribs = žebra, weapon = model zbraně z inventáře
             (id věci: basic_sword, boss_sword, wood_sword_1…), weaponColor = přebarvení zbraně, shield = id štítu
   look.body  tvar těla: 'humanoid' (výchozí, kostlivci), 'golem' (balvany a láva), 'slime' (průhledný sliz)
             golem: lava = barva lávy (0xff6a10 oranžová, 0xa040ff fialová), light = láva svítí do okolí
             slime: color = barva slizu, glow = vnitřní záře, barY = výška ukazatele životů
   boss      true = velký ukazatel životů nahoře na obrazovce, když s ním bojuješ
   radius    jak je příšera široká (hráč jí neprojde, větší = snáz ji trefíš)
   Pravidlo pro všechny příšery: zásah hráče nepřeruší rozběhnutý útok příšery (útok vždy dokončí).
*/
window.MONSTERS={
  skeleton:{
    name:'Kostlivec',hp:60,dmg:9,speed:2.3,walk:.9,aggro:9,leash:16,range:1.45,reach:1.9,
    windup:.6,atkDur:.95,cooldown:1.1,respawn:30,scale:1.05,
    look:{color:0xd8cfb6,eyes:0xff3030,ribs:true,weapon:'basic_sword',weaponColor:0x6b4a32}
  },
  skeleton_guard:{
    name:'Kostlivec strážce',hp:150,dmg:16,speed:1.8,walk:.7,aggro:8,leash:12,range:1.6,reach:2.2,
    windup:.85,atkDur:1.3,cooldown:1.6,respawn:60,scale:1.3,
    look:{color:0x9d988c,eyes:0x40e0ff,ribs:true,weapon:'boss_sword',weaponColor:0x3a3a40,shield:'wood_shield_3'}
  },
  magma_golem:{ // BOSS: hranatý kolos z tmavých balvanů, mezi kterými prosvítá láva
    name:'Magmový golem',boss:true,hp:1500,dmg:35,speed:1.3,walk:.5,aggro:14,leash:22,range:1.25,reach:1.55,
    windup:1.3,atkDur:2.1,cooldown:2.4,respawn:600,scale:3.2,radius:.55,
    look:{body:'golem',color:0x2e2826,lava:0xff6a10,light:true}
  },
  acid_slime:{ // poloprůhledná kyselinová kostka, uvnitř zaseklé kosti a starý meč
    name:'Kyselinový sliz',hp:90,dmg:12,speed:1.7,walk:.6,aggro:8,leash:14,range:1.3,reach:1.7,
    windup:.55,atkDur:.9,cooldown:1.4,respawn:40,scale:1.3,radius:.6,
    look:{body:'slime',color:0x7be04a,glow:0x2f8a18,barY:1.75}
  }
};
