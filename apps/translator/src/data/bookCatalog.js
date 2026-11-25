/**
 * NT/OT book catalog for Translator → LBF export.
 * MorphGNT filenames follow SBLGNT numbering (61-Mt … 87-Rev).
 */

export const NT_BOOKS = [
  { id: "matthew", label: "Matthew", morphFile: "61-Mt-morphgnt.txt", bleSlug: "mateo", usfm: "MAT", number: 40, bookCode: 40 },
  { id: "mark", label: "Mark", morphFile: "62-Mk-morphgnt.txt", bleSlug: "marcos", usfm: "MRK", number: 41, bookCode: 41 },
  { id: "luke", label: "Luke", morphFile: "63-Lk-morphgnt.txt", bleSlug: "lucas", usfm: "LUK", number: 42, bookCode: 42 },
  { id: "john", label: "John", morphFile: "64-Jn-morphgnt.txt", bleSlug: "juan", usfm: "JHN", number: 43, bookCode: 43 },
  { id: "acts", label: "Acts", morphFile: "65-Ac-morphgnt.txt", bleSlug: "hechos", usfm: "ACT", number: 44, bookCode: 44 },
  { id: "romans", label: "Romans", morphFile: "66-Ro-morphgnt.txt", bleSlug: "romanos", usfm: "ROM", number: 45, bookCode: 45 },
  { id: "1corinthians", label: "1 Corinthians", morphFile: "67-1Co-morphgnt.txt", bleSlug: "1corintios", usfm: "1CO", number: 46, bookCode: 46 },
  { id: "2corinthians", label: "2 Corinthians", morphFile: "68-2Co-morphgnt.txt", bleSlug: "2corintios", usfm: "2CO", number: 47, bookCode: 47 },
  { id: "galatians", label: "Galatians", morphFile: "69-Ga-morphgnt.txt", bleSlug: "galatas", usfm: "GAL", number: 48, bookCode: 48 },
  { id: "ephesians", label: "Ephesians", morphFile: "70-Eph-morphgnt.txt", bleSlug: "efesios", usfm: "EPH", number: 49, bookCode: 49 },
  { id: "philippians", label: "Philippians", morphFile: "71-Php-morphgnt.txt", bleSlug: "filipenses", usfm: "PHP", number: 50, bookCode: 50 },
  { id: "colossians", label: "Colossians", morphFile: "72-Col-morphgnt.txt", bleSlug: "colosenses", usfm: "COL", number: 51, bookCode: 51 },
  { id: "1thessalonians", label: "1 Thessalonians", morphFile: "73-1Th-morphgnt.txt", bleSlug: "1tesalonicenses", usfm: "1TH", number: 52, bookCode: 52 },
  { id: "2thessalonians", label: "2 Thessalonians", morphFile: "74-2Th-morphgnt.txt", bleSlug: "2tesalonicenses", usfm: "2TH", number: 53, bookCode: 53 },
  { id: "1timothy", label: "1 Timothy", morphFile: "75-1Ti-morphgnt.txt", bleSlug: "1timoteo", usfm: "1TI", number: 54, bookCode: 54 },
  { id: "2timothy", label: "2 Timothy", morphFile: "76-2Ti-morphgnt.txt", bleSlug: "2timoteo", usfm: "2TI", number: 55, bookCode: 55 },
  { id: "titus", label: "Titus", morphFile: "77-Tit-morphgnt.txt", bleSlug: "tito", usfm: "TIT", number: 56, bookCode: 56 },
  { id: "philemon", label: "Philemon", morphFile: "78-Phm-morphgnt.txt", bleSlug: "filemon", usfm: "PHM", number: 57, bookCode: 57 },
  { id: "hebrews", label: "Hebrews", morphFile: "79-Heb-morphgnt.txt", bleSlug: "hebreos", usfm: "HEB", number: 58, bookCode: 58 },
  { id: "james", label: "James", morphFile: "80-Jas-morphgnt.txt", bleSlug: "santiago", usfm: "JAS", number: 59, bookCode: 59 },
  { id: "1peter", label: "1 Peter", morphFile: "81-1Pe-morphgnt.txt", bleSlug: "1pedro", usfm: "1PE", number: 60, bookCode: 60 },
  { id: "2peter", label: "2 Peter", morphFile: "82-2Pe-morphgnt.txt", bleSlug: "2pedro", usfm: "2PE", number: 61, bookCode: 61 },
  { id: "1john", label: "1 John", morphFile: "83-1Jn-morphgnt.txt", bleSlug: "1juan", usfm: "1JN", number: 62, bookCode: 62 },
  { id: "2john", label: "2 John", morphFile: "84-2Jn-morphgnt.txt", bleSlug: "2juan", usfm: "2JN", number: 63, bookCode: 63 },
  { id: "3john", label: "3 John", morphFile: "85-3Jn-morphgnt.txt", bleSlug: "3juan", usfm: "3JN", number: 64, bookCode: 64 },
  { id: "jude", label: "Jude", morphFile: "86-Jud-morphgnt.txt", bleSlug: "judas", usfm: "JUD", number: 65, bookCode: 65 },
  { id: "revelation", label: "Revelation", morphFile: "87-Re-morphgnt.txt", bleSlug: "apocalipsis", usfm: "REV", number: 66, bookCode: 66 }
];

export const OT_BOOKS = [
  ["genesis", "Génesis", "Gen.xml", "GEN"], ["exodo", "Éxodo", "Exod.xml", "EXO"],
  ["levitico", "Levítico", "Lev.xml", "LEV"], ["numeros", "Números", "Num.xml", "NUM"],
  ["deuteronomio", "Deuteronomio", "Deut.xml", "DEU"], ["josue", "Josué", "Josh.xml", "JOS"],
  ["jueces", "Jueces", "Judg.xml", "JDG"], ["rut", "Rut", "Ruth.xml", "RUT"],
  ["1samuel", "1 Samuel", "1Sam.xml", "1SA"], ["2samuel", "2 Samuel", "2Sam.xml", "2SA"],
  ["1reyes", "1 Reyes", "1Kgs.xml", "1KI"], ["2reyes", "2 Reyes", "2Kgs.xml", "2KI"],
  ["1cronicas", "1 Crónicas", "1Chr.xml", "1CH"], ["2cronicas", "2 Crónicas", "2Chr.xml", "2CH"],
  ["esdras", "Esdras", "Ezra.xml", "EZR"], ["nehemias", "Nehemías", "Neh.xml", "NEH"],
  ["ester", "Ester", "Esth.xml", "EST"], ["job", "Job", "Job.xml", "JOB"],
  ["salmos", "Salmos", "Ps.xml", "PSA"], ["proverbios", "Proverbios", "Prov.xml", "PRO"],
  ["eclesiastes", "Eclesiastés", "Eccl.xml", "ECC"], ["cantares", "Cantares", "Song.xml", "SNG"],
  ["isaias", "Isaías", "Isa.xml", "ISA"], ["jeremias", "Jeremías", "Jer.xml", "JER"],
  ["lamentaciones", "Lamentaciones", "Lam.xml", "LAM"], ["ezequiel", "Ezequiel", "Ezek.xml", "EZK"],
  ["daniel", "Daniel", "Dan.xml", "DAN"], ["oseas", "Oseas", "Hos.xml", "HOS"],
  ["joel", "Joel", "Joel.xml", "JOL"], ["amos", "Amós", "Amos.xml", "AMO"],
  ["abdias", "Abdías", "Obad.xml", "OBA"], ["jonas", "Jonás", "Jonah.xml", "JON"],
  ["miqueas", "Miqueas", "Mic.xml", "MIC"], ["nahum", "Nahúm", "Nah.xml", "NAM"],
  ["habacuc", "Habacuc", "Hab.xml", "HAB"], ["sofonias", "Sofonías", "Zeph.xml", "ZEP"],
  ["hageo", "Hageo", "Hag.xml", "HAG"], ["zacarias", "Zechariah", "Zech.xml", "ZEC"],
  ["malaquias", "Malaquías", "Mal.xml", "MAL"]
].map(([slug, label, oshbFile, usfm], index) => ({
  id: slug === "jonas" ? "jonah" : (slug === "zacarias" ? "zechariah" : slug),
  label, oshbFile, bleSlug: slug, usfm, number: index + 1, bookCode: index + 1, spine: "oshb"
}));

export const OT_PILOT_BOOKS = OT_BOOKS.filter(book => ["genesis", "jonah"].includes(book.id));

/** OT books with an OSHB spine under alignment/ot/{slug}/ */
export const OSHB_SPINE_BOOKS = [
  {
    id: "daniel",
    label: "Daniel",
    bleSlug: "daniel",
    usfm: "DAN",
    number: 27,
    bookCode: 27,
    spine: "oshb"
  },
  {
    id: "zechariah",
    label: "Zechariah",
    bleSlug: "zacarias",
    usfm: "ZEC",
    number: 38,
    bookCode: 38,
    spine: "oshb"
  }
];

export function allTranslatorBooks() {
  return [...NT_BOOKS, ...OT_BOOKS];
}

export function lbfHome(book) {
  const slug = book.id === "titus" ? "titus" : book.bleSlug;
  const testament = Number(book.number) >= 40 ? "nt" : "ot";
  return { slug, testament };
}

function normalizedBookKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function findBook(idOrLabel) {
  const key = normalizedBookKey(idOrLabel);
  return allTranslatorBooks().find(b =>
    normalizedBookKey(b.id) === key
    || normalizedBookKey(b.label) === key
    || normalizedBookKey(b.bleSlug) === key
    || normalizedBookKey(b.usfm) === key
  ) || null;
}

export function sourceTokenId(bookCode, chapter, verse, position) {
  return `n${String(bookCode).padStart(2, "0")}${String(chapter).padStart(3, "0")}${String(verse).padStart(3, "0")}${String(position).padStart(3, "0")}`;
}
