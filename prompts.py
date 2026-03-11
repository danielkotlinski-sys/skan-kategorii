"""
Prompty do analizy kategorii.

Zasada: żadnych banalnych obserwacji.
Szukamy strukturalnych założeń — niepisanych reguł, które kategoria bierze
za pewnik, a które są decyzjami podjętymi kiedyś przez kogoś, nie prawami natury.
"""


PROMPT_ANALYZE_MAIN_COMPETITOR = """\
Jesteś strategiem marki. Analizujesz firmę z kategorii: {category}.

TREŚĆ ICH STRONY:
{content}

Wypełnij analizę w JSON. Pisz konkretnie i obserwacyjnie — nie oceniaj, opisuj.

{{
  "dominujaca_obietnica": "Jedno zdanie: co ta firma obiecuje klientowi jako główną wartość. \
Cytuj lub parafrazuj ich własny język — nie interpretuj.",
  "slowa_klucze": ["5-7 słów lub fraz, które powtarzają się najczęściej w ich komunikacji"],
  "do_kogo_mowia": "Do kogo mówi ta firma — nie demograficznie, ale psychograficznie. \
Jaką tożsamość lub problem zakładają u swojego klienta? 2-3 zdania.",
  "jak_uzasadniaja_wartosc": "Co jest ich 'dowodem'? Liczby, certyfikaty, case studies, \
lata doświadczenia, zespół, klienci? Co ma sprawić, że uwierzysz? 2-3 zdania.",
  "co_przemilczaja": "Czego ta firma NIGDY nie powie na głos — choć każdy w branży to wie. \
Jakie ryzyko, koszt lub ograniczenie jest nieobecne w komunikacji? 2-3 zdania.",
  "co_frustrujacego": "Gdybyś był klientem tej firmy i miał inne oczekiwania niż zakłada \
ich model — co byłoby dla Ciebie frustrujące w tym podejściu? 2-3 zdania."
}}

Odpowiedz WYŁĄCZNIE JSONem. Żadnych komentarzy przed ani po.\
"""


PROMPT_ANALYZE_SMALL_COMPETITOR = """\
Krótka analiza mniejszej firmy z kategorii: {category}.

TREŚĆ ICH STRONY:
{content}

JSON:
{{
  "co_robi_inaczej": "Czym wyróżnia się od dominującego wzorca w kategorii, jeśli w ogóle. \
Jeśli niczym — napisz to wprost. 1-2 zdania.",
  "czy_lamie_konwencje": "wzmacnia / łamie / pośrednie",
  "jak_lamie": "Jeśli łamie konwencję — w jaki konkretny sposób? Jeśli nie — null."
}}

Tylko JSON.\
"""


PROMPT_SYNTHESIZE_CATEGORY = """\
Jesteś strategiem marki. Przeprowadziłeś analizę kategorii: "{category}" ({market}).
Przejrzałeś {n_main} głównych i {n_small} mniejszych graczy.

ZEBRANE DANE:
{analyses_text}

---

ZADANIE: Synteza strategiczna konwencji kategorii.

WAŻNA INSTRUKCJA dotycząca jakości:
Unikaj obserwacji, które brzmią jak: "firmy podkreślają profesjonalizm i doświadczenie",
"komunikacja skupia się na jakości", "wszyscy obiecują dobre wyniki".
To są truizmy — każda branża tak wygląda z zewnątrz.

Szukaj głębiej. Pytaj: co ta kategoria milcząco ZAKŁADA o świecie i o kliencie?
Jakie niepisane reguły organizują całą logikę wartości w tej branży?
Co musiałoby być prawdą, żeby ta konwencja miała sens?
Gdzie jest strukturalna sprzeczność między tym, co kategoria obiecuje, a tym, co faktycznie dostarcza?

Przykład dobrej obserwacji (z innej kategorii):
"Rynek coachingu zakłada, że klient zna już swój problem i potrzebuje tylko narzędzi —
dlatego nikt nie mówi o diagnozie. To strukturalnie wyklucza klientów, którzy nie wiedzą,
co im przeszkadza."

Przykład banalnej obserwacji:
"Coachowie podkreślają skuteczność i indywidualne podejście."

---

Wypełnij syntezę w JSON:

{{
  "dominujaca_definicja_wartosci": "Za co klienci NAPRAWDĘ płacą w tej kategorii? \
Nie co firmy obiecują — jaka jest ukryta logika wymiany wartości? \
Co musiałby poczuć lub osiągnąć klient, żeby powiedzieć 'to był dobry wybór'? \
3-4 zdania, strategicznie, nieoczywiste.",

  "konwencje": [
    {{
      "nazwa": "Krótka nazwa konwencji (3-5 słów)",
      "co_wszyscy_robia": "Opis wzorca — co konkretnie robią wszyscy lub prawie wszyscy. \
Nie 'dbają o jakość', ale co faktycznie jest takie samo w modelu obsługi, obietnicy, \
strukturze oferty. 2-3 zdania.",
      "skad_sie_wzelo": "Historyczne lub logiczne źródło tej konwencji. Dlaczego ktoś \
kiedyś tak zrobił — i dlaczego inni skopiowali? 1-2 zdania.",
      "co_kosztuje_klienta": "Jakie potrzeby ta konwencja strukturalnie ignoruje? \
Kto przez nią odpada? Co klient musi odpuścić, żeby wejść w ten model? 2-3 zdania."
    }},
    {{ "nazwa": "...", "co_wszyscy_robia": "...", "skad_sie_wzelo": "...", "co_kosztuje_klienta": "..." }},
    {{ "nazwa": "...", "co_wszyscy_robia": "...", "skad_sie_wzelo": "...", "co_kosztuje_klienta": "..." }}
  ],

  "skrypt_kategorii": "Napisz 3-4 zdania, które brzmią jak opis TYPOWEJ firmy z tej kategorii. \
Użyj języka i obietnic, które widziałeś najczęściej. Powinno pasować do minimum 4 z 5 firm. \
To jest 'konwencjonalny opis' — skrypt, który wszyscy powtarzają.",

  "tabu_kategorii": [
    "Temat, problem lub stwierdzenie, którego nikt w kategorii nie wypowiada na głos — \
choć wszyscy go znają. Konkretne zdanie, nie abstrakcja.",
    "...",
    "...",
    "...",
    "..."
  ],

  "klient_wykluczony": "Kto NIE jest obsługiwany przez obecny model kategorii? \
Kim jest ta osoba, co ją strukturalnie wyklucza, czego chce a nie dostaje? 3-4 zdania."
}}

Odpowiedz WYŁĄCZNIE JSONem.\
"""


PROMPT_CLIENT_PROFILE = """\
Na podstawie analizy konwencji kategorii "{category}", zbuduj profil motywacyjno-behawioralny
klienta, dla którego ta konwencja jest ATRAKCYJNA — i zidentyfikuj napięcie strategiczne.

SYNTEZA KATEGORII:
Dominująca definicja wartości: {dominujaca_def}

Konwencje kategorii:
{konwencje_text}

Tabu:
{tabu_text}

Klient wykluczony: {klient_wykluczony}

---

INSTRUKCJA:

To NIE jest profil demograficzny (wiek, płeć, dochód).
To jest profil psychologiczny — jakie wartości, lęki, mechanizmy decyzyjne i narracje
sprawiają, że ta konwencja kategorii działa na tego klienta.

Wzorzec dobrej analizy — przykład z kosmetyków naturalnych:

"Konwencja (naturalne składniki / brak chemii / wegańskie formuły) zakłada klienta,
który traktuje zakup jako akt tożsamościowy — wybierając markę, potwierdza swoje wartości,
a nie tylko zaspokaja potrzebę. Decyzja jest legitymizowana przez skład, nie przez efekt.
Ten klient odczuwa niepokój związany z niekontrolowanymi substancjami — ryzyko jest
niewidoczne, więc konwencja odpowiada na lęk, nie na problem.

To przyciąga miliony. Ale strukturalnie wyklucza klienta nastawionego na skuteczność
ponad ideologię — kogoś, kto pyta 'czy to działa?' zanim zapyta 'z czego to jest zrobione'.
Napięcie strategiczne tkwi tu: rynek naturalnych kosmetyków zbudował język moralny
(dobry/zły skład), który jest jednocześnie jego siłą i ślepą plamką."

---

Wypełnij profil w JSON:

{{
  "czego_naprawde_chce": "Głęboka motywacja — nie 'dobrego produktu', ale jaką potrzebę \
egzystencjalną, tożsamościową lub emocjonalną napędza wybór w tej kategorii. \
Co ten klient chce poczuć lub przestać czuć po zakupie? 3-4 zdania.",

  "czego_sie_boi": "Co go niepokoi? Jakie ryzyko zarządza przez wybór firm z tej kategorii? \
Co by go zawstydziło, co kosztuje go zła decyzja — finansowo, społecznie lub emocjonalnie? \
2-3 zdania.",

  "jak_decyduje": "Po czym poznaje, że wybrał dobrze? Jakie sygnały dają mu pewność \
jeszcze przed zakupem? Co jest dla niego 'dowodem wartości' — skład, referencje, \
wygląd, certyfikaty, cena, podejście? 2-3 zdania.",

  "historia_ktora_opowiada_sobie": "Narracja, którą klient buduje wokół swojego wyboru — \
w pierwszej osobie, jak opowiedziałby o tym znajomemu lub sam sobie. \
1-2 zdania w cudzysłowie, konkretne i ludzkie.",

  "kogo_strukturalnie_wyklucza": "Kto jest po drugiej stronie — jaka motywacja, \
jakie wartości, jakie oczekiwania sprawiają, że konwencja NIE trafia do określonej grupy. \
Nie demografia — psychografia. 3-4 zdania.",

  "napiecie_strategiczne": "Gdzie tkwi fundamentalne napięcie między tym, kogo konwencja \
obsługuje, a tym, kogo wyklucza? Co ta sprzeczność mówi o możliwej przestrzeni strategicznej? \
Czy to napięcie da się rozwiązać, czy jest strukturalne? 3-4 zdania."
}}

Odpowiedz WYŁĄCZNIE JSONem. Bądź odkrywczy i konkretny — unikaj ogólników.\
"""
