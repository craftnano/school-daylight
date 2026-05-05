# Positive-Content Surfacing Diagnostic — full 2,532-school population

Read-only scan of raw Phase 4 findings (`context.findings` + `district_context.findings`, pre-Stage 0/1) against a positive-content vocabulary, with pipeline-disposition trace per match.

## What the Phase 4 prompts ask for

`prompts/context_enrichment_v1.txt` line 16 names **`awards_recognition`** as a category to search: *"Awards, grants, recognitions, honors, Blue Ribbon, Green Ribbon, or other formal recognition."* Line 18 names **`programs`**: *"Notable programs, initiatives, partnerships, or curriculum changes."*

`prompts/district_enrichment_v1.txt` mirrors this at district scope.

**The categories exist in the schema and are named in the search instructions, but the prompts do NOT actively target the specific positive-content vocabulary in the diagnostic list.** Haiku is told *recognition is one category to search for* alongside news, investigations, leadership, programs, community investment, and other. It is not given examples like 'Washington Achievement Award' or 'Knowledge Bowl state finalists' or 'Math Counts champions' to anchor the search. Coverage is whatever Haiku surfaces unprompted.

## Stage 1 explicitly excludes positive findings

`prompts/layer3_stage1_haiku_triage_v1.txt` line 37: *"Awards, recognitions, and positive achievements: exclude unless directly relevant to an adverse finding (e.g., an award that was later revoked, a program cited in a lawsuit)."* This is a categorical exclusion in the editorial-triage stage. Even if Phase 4 captures positive content, Stage 1 systematically removes it from the parent-facing narrative unless tied to an adverse signal.

## Headline numbers

- **Schools with at least one positive-content match in raw Phase 4 findings:** 185 / 2532 (7.3%)
- **Schools whose final `layer3_narrative` text contains at least one positive-content match:** 1 / 2532 (0.0%)
- **Total positive-content matches across all raw findings:** 239

## Pipeline disposition of matches

| Disposition | Match count | Unique schools |
|---|---:|---:|
| stage1_excluded | 202 | 157 |
| stage1_filtered_to_zero (no included) | 31 | 24 |
| stage0_dropped | 5 | 4 |
| in_final_narrative | 1 | 1 |

## Distribution by Phase 4 category assignment

| Category | Match count |
|---|---:|
| awards_recognition | 167 |
| programs | 62 |
| leadership | 6 |
| other | 3 |
| news | 1 |

## Top vocabulary matches by frequency

| Vocabulary label | Hits |
|---|---:|
| Dual immersion / dual language | 51 |
| Schools of Distinction | 36 |
| Achievement Award (general) | 33 |
| Green Ribbon | 24 |
| Blue Ribbon | 21 |
| Washington Achievement Award | 20 |
| National Blue Ribbon | 13 |
| Teacher of the Year | 11 |
| International Baccalaureate | 10 |
| FIRST competition | 5 |
| State champion | 5 |
| Title I Distinguished | 5 |
| Science Olympiad state+ | 1 |
| National champion | 1 |
| National Board Certified | 1 |
| Magnet school | 1 |
| Career pathway | 1 |

## Per-school detail (every match)

| NCES | School | District | Vocabulary | Phase 4 category | Disposition | Snippet |
|------|--------|----------|------------|------------------|-------------|---------|
| `530003000008` | McDermoth Elementary | Aberdeen School District | Achievement Award (general) | awards_recognition | stage1_excluded | mentary received a Washington Achievement Award in April 2014.... |
| `530003000008` | McDermoth Elementary | Aberdeen School District | Washington Achievement Award | awards_recognition | stage1_excluded | Dermoth Elementary received a Washington Achievement Award in April 2014.... |
| `530024001190` | Kent Prairie Elementary | Arlington School District | Achievement Award (general) | awards_recognition | stage1_filtered_to_zero (no included) | received the Washington State Achievement Award in 2012, 2013, 2014, and 2015... |
| `530033003110` | Eagle Harbor High School | Bainbridge Island School District | Schools of Distinction | awards_recognition | stage1_excluded |  School has been awarded the 'Schools of Distinction' designation four times by ... |
| `530033000044` | Halilts Elementary School | Bainbridge Island School District | Achievement Award (general) | awards_recognition | stage1_excluded | entary) received a Washington Achievement Award for the 2016 academic school ... |
| `530033000044` | Halilts Elementary School | Bainbridge Island School District | Washington Achievement Award | awards_recognition | stage1_excluded | Wilkes Elementary) received a Washington Achievement Award for the 2016 academic... |
| `530033002523` | Odyssey Multiage Program | Bainbridge Island School District | Achievement Award (general) | awards_recognition | stage1_excluded | e Program earned a Washington Achievement Award for the 2016 Academic School ... |
| `530033002523` | Odyssey Multiage Program | Bainbridge Island School District | Washington Achievement Award | awards_recognition | stage1_excluded | sey Multiage Program earned a Washington Achievement Award for the 2016 Academic... |
| `530033000047` | Ordway Elementary | Bainbridge Island School District | Achievement Award (general) | awards_recognition | stage1_excluded | ary received Washington State Achievement Awards for the 2015 academic year a... |
| `530038002782` | CAM Academy | Battle Ground School District | Achievement Award (general) | awards_recognition | stage1_excluded | emy has earned the Washington Achievement Award for Overall Excellence every ... |
| `530038002782` | CAM Academy | Battle Ground School District | Washington Achievement Award | awards_recognition | stage1_excluded | CAM Academy has earned the Washington Achievement Award for Overall Excellence e... |
| `530039000062` | Bennett Elementary School | Bellevue School District | Dual immersion / dual language | programs | stage1_excluded | me of the elementary Japanese Dual Language program starting in the 2025-... |
| `530039000068` | Highland Middle School | Bellevue School District | Dual immersion / dual language | programs | stage1_excluded | ded two of Highland's Spanish Dual Language teachers with scholarships fo... |
| `530039003149` | International School | Bellevue School District | Blue Ribbon | awards_recognition | stage1_excluded | onal School was selected as a Blue Ribbon National School of Excellence... |
| `530039000075` | Lake Hills Elementary | Bellevue School District | Dual immersion / dual language | awards_recognition | stage1_excluded | s recognition for its Spanish Dual Language program.... |
| `530039000078` | Newport Senior High School | Bellevue School District | Blue Ribbon | awards_recognition | stage1_excluded | High School was selected as a Blue Ribbon School of Excellence in 2003 ... |
| `530039000079` | Odle Middle School | Bellevue School District | Blue Ribbon | awards_recognition | stage1_excluded |  U.S. Department of Education Blue Ribbon Award in the 2001-02 school y... |
| `530039000088` | Spiritridge Elementary School | Bellevue School District | Schools of Distinction | awards_recognition | stage1_excluded | ary School received the 2013 'School of Distinction' Award for the third consecu... |
| `530039000093` | Tillicum Middle School | Bellevue School District | Dual immersion / dual language | programs | stage1_excluded | llicum Middle School operates dual language programs in Spanish and Manda... |
| `530042000098` | Alderwood Elementary School | Bellingham School District | Achievement Award (general) | awards_recognition | stage1_excluded | chool received the Washington Achievement Award for Overall Excellence in bot... |
| `530042000098` | Alderwood Elementary School | Bellingham School District | Washington Achievement Award | awards_recognition | stage1_excluded | Year. The school received the Washington Achievement Award for Overall Excellenc... |
| `530042000108` | Lowell Elementary School | Bellingham School District | International Baccalaureate | awards_recognition | stage1_excluded | owell Elementary School is an International Baccalaureate Candidate school and i... |
| `530042002939` | Northern Heights Elementary Schl | Bellingham School District | International Baccalaureate | awards_recognition | stage1_excluded | to be authorized to offer the International Baccalaureate Primary Years Program,... |
| `530042000110` | Parkview Elementary School | Bellingham School District | Achievement Award (general) | awards_recognition | stage1_excluded | School won a Washington State Achievement award for excellence in growth over... |
| `530042000113` | Sehome High School | Bellingham School District | Teacher of the Year | awards_recognition | stage1_excluded | arned the 2025 State Language Teacher of the Year award from the Washington Ass... |
| `530042000115` | Silver Beach Elementary School | Bellingham School District | Achievement Award (general) | awards_recognition | stage1_excluded | gnition from Washington State Achievement Awards 2014 for reading growth, pla... |
| `530048001748` | Evergreen Elementary | Bethel School District | Blue Ribbon | awards_recognition | stage1_excluded | mentary received the National Blue Ribbon Award for Academic Excellence... |
| `530048001748` | Evergreen Elementary | Bethel School District | National Blue Ribbon | awards_recognition | stage1_excluded | green Elementary received the National Blue Ribbon Award for Academic Excellence... |
| `530081002512` | Skyridge Middle School | Camas School District | Achievement Award (general) | awards_recognition | stage1_excluded | ol was awarded the Washington Achievement Award from 2009 through 2016, recog... |
| `530081002512` | Skyridge Middle School | Camas School District | Washington Achievement Award | awards_recognition | stage1_excluded | Middle School was awarded the Washington Achievement Award from 2009 through 201... |
| `530111000194` | Greenacres Elementary | Central Valley School District | Schools of Distinction | awards_recognition | stage1_excluded |  is designated as a two-time 'School of Distinction,' indicating formal recognit... |
| `530132002433` | Heights Elementary | Clarkston School District | Achievement Award (general) | awards_recognition | stage1_filtered_to_zero (no included) |  Washington State's School of Achievement Award, placing in the top five-perc... |
| `530141002839` | Alfaretta House | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000246` | Beachwood Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003535` | CPSD Open Doors Program | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000247` | Carter Lake Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003549` | Clover Park Early Learning Program | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000250` | Clover Park High School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000251` | Custer Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000252` | Dower Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141002438` | Evergreen Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000271` | Firwood | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003516` | Four Heroes Elementary | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003000` | General William H. Harrison Preparatory School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003920` | Gravelly Lake K-12 Academy | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000256` | Hillside Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000257` | Hudtloff Middle School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000258` | Idlewild Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000260` | Lake Louise Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000261` | Lakes High School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000262` | Lakeview Hope Academy | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000263` | Lochburn Middle School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003473` | Meriwether Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141001897` | Oak Grove | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000265` | Oakbrook Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003402` | Oakridge Group Home | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141002581` | Park Lodge Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003472` | Rainier Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141002860` | Re-Entry High School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141002861` | Re-Entry Middle School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141002862` | Special Education Services/relife | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000272` | Thomas Middle School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000158` | Tillicum Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141003396` | Transition Day Students | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530141000270` | Tyee Park Elementary School | Clover Park School District | Dual immersion / dual language | programs | stage1_excluded | PSD is planning for a two-way dual language program with a balance of bil... |
| `530201000302` | Davenport Elementary | Davenport School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) | 018), and received Washington School of Distinction awards in 2011, 2015, 2017, ... |
| `530201000303` | Davenport Senior High School | Davenport School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) | 018), and received Washington School of Distinction awards in 2011, 2015, 2017, ... |
| `530201003897` | LINCOLN COUNTY PATHWAYS ACADEMY | Davenport School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) | 018), and received Washington School of Distinction awards in 2011, 2015, 2017, ... |
| `530201003705` | Lincoln County Tech | Davenport School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) | 018), and received Washington School of Distinction awards in 2011, 2015, 2017, ... |
| `530201003752` | Lincoln County Virtual Academy | Davenport School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) | 018), and received Washington School of Distinction awards in 2011, 2015, 2017, ... |
| `530240001189` | Challenge Elementary | Edmonds School District | Blue Ribbon | awards_recognition | stage1_excluded | ral recognition as a National Blue Ribbon School, designating it as a h... |
| `530240001189` | Challenge Elementary | Edmonds School District | National Blue Ribbon | awards_recognition | stage1_excluded | ived federal recognition as a National Blue Ribbon School, designating it as a h... |
| `530267000393` | Eisenhower Middle School | Everett School District | Achievement Award (general) | awards_recognition | stage1_excluded | recognition in the Washington Achievement Awards, as announced by Everett Sch... |
| `530267000393` | Eisenhower Middle School | Everett School District | Washington Achievement Award | awards_recognition | stage1_excluded | Excellence recognition in the Washington Achievement Awards, as announced by Eve... |
| `530267001725` | Gateway Middle School | Everett School District | Achievement Award (general) | awards_recognition | stage1_excluded | ddle School earned Washington Achievement Awards recognition for Overall Exce... |
| `530267001725` | Gateway Middle School | Everett School District | Washington Achievement Award | awards_recognition | stage1_excluded | Gateway Middle School earned Washington Achievement Awards recognition for Overa... |
| `530267001726` | Henry M. Jackson High School | Everett School District | FIRST competition | programs | stage1_excluded | chool's robotics team won the FIRST Robotics world championship in 2025, m... |
| `530267002897` | Port Gardner | Everett School District | Achievement Award (general) | awards_recognition | stage1_excluded | p program earned a Washington Achievement Award with Special Recognition for ... |
| `530267002897` | Port Gardner | Everett School District | Washington Achievement Award | awards_recognition | stage1_excluded |  Partnership program earned a Washington Achievement Award with Special Recognit... |
| `530267000409` | Silver Lake Elementary | Everett School District | Dual immersion / dual language | programs | stage1_excluded | lver Lake Elementary offers a Dual Language Spanish Immersion Program at ... |
| `530267000411` | Whittier Elementary | Everett School District | Blue Ribbon | awards_recognition | stage1_excluded | er Elementary earned National Blue Ribbon School designation, one of th... |
| `530267000411` | Whittier Elementary | Everett School District | National Blue Ribbon | awards_recognition | stage1_excluded | Whittier Elementary earned National Blue Ribbon School designation, one of th... |
| `530267001792` | Woodside Elementary | Everett School District | Achievement Award (general) | awards_recognition | stage1_excluded |  has been awarded the state's achievement award 4 years in a row, with teache... |
| `530282000432` | Camelot Elementary School | Federal Way School District | Blue Ribbon | awards_recognition | stage1_excluded | ved recognition as a National Blue Ribbon School. The school had previo... |
| `530282000432` | Camelot Elementary School | Federal Way School District | National Blue Ribbon | awards_recognition | stage1_excluded | ool received recognition as a National Blue Ribbon School. The school had previo... |
| `530282000442` | Lakota Middle School | Federal Way School District | Green Ribbon | awards_recognition | stage1_excluded |  U.S. Department of Education Green Ribbon School Award, one of only 47 ... |
| `530282000450` | Sunnycrest Elementary School | Federal Way School District | Dual immersion / dual language | programs | stage1_excluded | t Elementary offers a Spanish dual language program as a core part of its... |
| `530282000451` | Thomas Jefferson High School | Federal Way School District | International Baccalaureate | programs | stage1_excluded | School has been an authorized International Baccalaureate Diploma school continu... |
| `530285000457` | Beach Elem | Ferndale School District | International Baccalaureate | programs | stage1_excluded | ementary was authorized as an International Baccalaureate Primary Years Programm... |
| `530285000458` | Central Elementary | Ferndale School District | Schools of Distinction | awards_recognition | stage1_excluded |  Elementary School received a School of Distinction award from the Center for Ed... |
| `530354000526` | Evergreen High School | Highline School District | Dual immersion / dual language | programs | stage1_excluded | een High School operates as a dual language school and offers integrated ... |
| `530354003742` | Highline Public Schools Virtual Academy | Highline School District | Teacher of the Year | awards_recognition | stage1_excluded |  was named the 2025 Gold Star Teacher of the Year. He was recognized for creati... |
| `530375001495` | Beaver Lake Middle School | Issaquah School District | FIRST competition | awards_recognition | stage1_excluded | d Alpha Intelligence, won the FIRST Tech Challenge Washington State Championship... |
| `530375001495` | Beaver Lake Middle School | Issaquah School District | State champion | awards_recognition | stage1_excluded | RST Tech Challenge Washington State Championship on January 28, 2023, with... |
| `530375003067` | Grand Ridge Elementary | Issaquah School District | Achievement Award (general) | awards_recognition | stage1_excluded | uction with a 2016 Washington Achievement Award in three categories.... |
| `530375003067` | Grand Ridge Elementary | Issaquah School District | Washington Achievement Award | awards_recognition | stage1_excluded | ublic Instruction with a 2016 Washington Achievement Award in three categories.... |
| `530375000574` | Issaquah High School | Issaquah School District | State champion | awards_recognition | stage1_excluded | petition and were WCTSMA Team State Champions.... |
| `530375000579` | Maywood Middle School | Issaquah School District | FIRST competition | programs | stage1_excluded | ovate Award respectively at a FIRST Tech Challenge competition.... |
| `530393000599` | Eastgate Elementary School | Kennewick School District | Dual immersion / dual language | leadership | stage1_excluded |  the school's transition to a dual language (English/Spanish) program.... |
| `530393003647` | Fuerza Elementary | Kennewick School District | Dual immersion / dual language | programs | stage1_excluded | Fuerza Elementary operates a Dual Language Program, as indicated on the ... |
| `530393000603` | Highlands Middle School | Kennewick School District | Science Olympiad state+ | programs | stage1_excluded |  School District to operate a Science Olympiad team, which has qualified for sta... |
| `530396001142` | Cedar Heights Middle School | Kent School District | Schools of Distinction | awards_recognition | stage1_excluded | le School was recognized as a School of Distinction for Growth in Literacy and M... |
| `530396002112` | Martin Sortun Elementary School | Kent School District | Achievement Award (general) | awards_recognition | stage1_excluded | eceived three 2014 Washington Achievement Awards, winning for overall excelle... |
| `530396002112` | Martin Sortun Elementary School | Kent School District | Title I Distinguished | awards_recognition | stage1_excluded | untry to receive the National Title I Distinguished School Award.</cite> Additio... |
| `530396002112` | Martin Sortun Elementary School | Kent School District | Washington Achievement Award | awards_recognition | stage1_excluded | he school received three 2014 Washington Achievement Awards, winning for overall... |
| `530396002799` | Millennium Elementary School | Kent School District | Green Ribbon | awards_recognition | stage1_excluded | .S. Department of Education's Green Ribbon School Award.... |
| `530420001906` | North Lake Middle School | Lake Stevens School District | Schools of Distinction | awards_recognition | stage1_excluded | ddle School received the 2012 School of Distinction Award from The Center for Ed... |
| `530423000670` | Juanita High School | Lake Washington School District | Achievement Award (general) | awards_recognition | stage1_excluded | ool won its fourth Washington Achievement Award Special Recognition for its e... |
| `530423000670` | Juanita High School | Lake Washington School District | Washington Achievement Award | awards_recognition | stage1_excluded | ta High School won its fourth Washington Achievement Award Special Recognition f... |
| `530423000674` | Lake Washington High School | Lake Washington School District | Blue Ribbon | awards_recognition | stage0_dropped |  was recognized as a National Blue Ribbon School in 1984-1985, one of t... |
| `530423000674` | Lake Washington High School | Lake Washington School District | National Blue Ribbon | awards_recognition | stage0_dropped | gh School was recognized as a National Blue Ribbon School in 1984-1985, one of t... |
| `530423003432` | Nikola Tesla STEM High School | Lake Washington School District | Achievement Award (general) | awards_recognition | stage1_excluded | gh School earned whole-school achievement awards for the 2023-24 and 2024-25 ... |
| `530423003432` | Nikola Tesla STEM High School | Lake Washington School District | FIRST competition | awards_recognition | stage1_excluded | 's robotics team won the 2024 FIRST Robotics Competition Washington Girls ... |
| `530423003077` | Rosa Parks Elementary | Lake Washington School District | Blue Ribbon | awards_recognition | stage1_excluded | recognized as a 2021 National Blue Ribbon School by U.S. Secretary of E... |
| `530423003077` | Rosa Parks Elementary | Lake Washington School District | National Blue Ribbon | awards_recognition | stage1_excluded | hool was recognized as a 2021 National Blue Ribbon School by U.S. Secretary of E... |
| `530423000683` | Rose Hill Middle School | Lake Washington School District | Achievement Award (general) | awards_recognition | stage1_excluded | ool received Washington State Achievement Awards from the Washington Board of... |
| `530543002128` | Challenger Elementary | Mukilteo School District | Dual immersion / dual language | programs | stage1_excluded | om for students with ASD, and Dual Language Kindergarten programs, as des... |
| `530543003162` | Odyssey Elementary | Mukilteo School District | Achievement Award (general) | awards_recognition | stage1_excluded | lementary received Washington Achievement Awards annually from 2010 through 2... |
| `530543003162` | Odyssey Elementary | Mukilteo School District | Washington Achievement Award | awards_recognition | stage1_excluded | Odyssey Elementary received Washington Achievement Awards annually from 2010 thr... |
| `530549000826` | Napavine Elementary | Napavine School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) |  received the designation of 'School of Distinction' awarded by the Washington S... |
| `530549000827` | Napavine Jr Sr High School | Napavine School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) |  received the designation of 'School of Distinction' awarded by the Washington S... |
| `530585000870` | Olympic View Elementary | North Thurston Public Schools | Schools of Distinction | awards_recognition | stage1_excluded | iew Elementary has earned the School of Distinction award for three consecutive ... |
| `530591000884` | Inglemoor HS | Northshore School District | Blue Ribbon | awards_recognition | stage1_excluded | became a No Child Left Behind Blue Ribbon School in 2007 for its consis... |
| `530591000884` | Inglemoor HS | Northshore School District | International Baccalaureate | programs | stage1_excluded | Inglemoor's International Baccalaureate program is one of the largest... |
| `530591000884` | Inglemoor HS | Northshore School District | National champion | programs | stage1_excluded | s attended the USRowing Youth National Champions four times: 2022, 2023, 2024... |
| `530591000885` | Kenmore Elementary | Northshore School District | National Board Certified | awards_recognition | stage1_excluded | re Elementary School received National Board Certification from the National Boa... |
| `530591000888` | Lockwood Elementary | Northshore School District | Achievement Award (general) | awards_recognition | stage1_excluded | gnized with a 2016 Washington Achievement Award by the Office of the Superint... |
| `530591000888` | Lockwood Elementary | Northshore School District | Washington Achievement Award | awards_recognition | stage1_excluded | ry was recognized with a 2016 Washington Achievement Award by the Office of the ... |
| `530591000892` | Secondary Academy for Success | Northshore School District | Green Ribbon | awards_recognition | stage1_excluded | award in 2012 and was named a Green Ribbon school by the Department of E... |
| `530594000898` | Broad View Elementary | Oak Harbor School District | Green Ribbon | awards_recognition | stage1_excluded |  U.S. Department of Education Green Ribbon School for its sustainability... |
| `530618000923` | Capital High School | Olympia School District | Blue Ribbon | awards_recognition | stage1_excluded | tal High School is a National Blue Ribbon award winner at the 9-12 grad... |
| `530618000923` | Capital High School | Olympia School District | National Blue Ribbon | awards_recognition | stage1_excluded | Capital High School is a National Blue Ribbon award winner at the 9-12 grad... |
| `530618000927` | Leland P Brown Elementary | Olympia School District | Teacher of the Year | leadership | stage1_excluded | y, was selected as a 2025 OSD Teacher of the Year and has been recognized for h... |
| `530000702914` | Clallam Co Juvenile Detention | Olympic Educational Service District 114 | Teacher of the Year | awards_recognition | stage1_filtered_to_zero (no included) | l presented the 2026 Regional Teacher of the Year Award to Shannon Green, a sec... |
| `530000702927` | Kitsap Co Detention Ctr | Olympic Educational Service District 114 | Teacher of the Year | awards_recognition | stage1_filtered_to_zero (no included) | l presented the 2026 Regional Teacher of the Year Award to Shannon Green, a sec... |
| `530630002869` | OASIS K-12 | Orcas Island School District | Schools of Distinction | programs | stage1_filtered_to_zero (no included) | Island High School received a School of Distinction award for achieving top five... |
| `530630000944` | Orcas Island Elementary School | Orcas Island School District | Schools of Distinction | programs | stage1_filtered_to_zero (no included) | Island High School received a School of Distinction award for achieving top five... |
| `530630000945` | Orcas Island High School | Orcas Island School District | Schools of Distinction | programs | stage1_filtered_to_zero (no included) | Island High School received a School of Distinction award for achieving top five... |
| `530630002815` | Orcas Island Middle School | Orcas Island School District | Schools of Distinction | programs | stage1_filtered_to_zero (no included) | Island High School received a School of Distinction award for achieving top five... |
| `530630003696` | Orcas Island Montessori Public | Orcas Island School District | Schools of Distinction | programs | stage1_filtered_to_zero (no included) | Island High School received a School of Distinction award for achieving top five... |
| `530630000946` | Waldron Island School | Orcas Island School District | Schools of Distinction | programs | stage1_filtered_to_zero (no included) | Island High School received a School of Distinction award for achieving top five... |
| `530033903495` | Innovation High School | PRIDE Prep Charter School District | International Baccalaureate | news | stage1_excluded | g emphasis on a more rigorous International Baccalaureate program.... |
| `530657001860` | James McGee Elementary | Pasco School District | Achievement Award (general) | awards_recognition | stage1_excluded | d honored with the Washington Achievement Award, the highest state honor for ... |
| `530657001860` | James McGee Elementary | Pasco School District | Schools of Distinction | awards_recognition | stage1_excluded | ary has been recognized as a "School of Distinction" by the Center for Education... |
| `530657001860` | James McGee Elementary | Pasco School District | Washington Achievement Award | awards_recognition | stage1_excluded | tiveness and honored with the Washington Achievement Award, the highest state ho... |
| `530657002950` | Maya Angelou Elementary | Pasco School District | Dual immersion / dual language | programs | stage1_excluded | sco School District's Two-Way Dual Language Program.... |
| `530657002785` | Rowena Chess Elementary | Pasco School District | Achievement Award (general) | awards_recognition | stage1_excluded | ry earned the 2013 Washington Achievement Award with Special Recognition for ... |
| `530657002785` | Rowena Chess Elementary | Pasco School District | Washington Achievement Award | awards_recognition | stage1_excluded | ss Elementary earned the 2013 Washington Achievement Award with Special Recognit... |
| `530669000980` | Artondale Elementary School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669000980` | Artondale Elementary School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded |  U.S. Department of Education Green Ribbon School in 2023, honored for i... |
| `530669000981` | Discovery Elementary School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669000982` | Evergreen Elementary | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669000982` | Evergreen Elementary | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded |  U.S. Department of Education Green Ribbon School award, one of only two... |
| `530669001793` | Gig Harbor High | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669000983` | Goodman Middle School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669000984` | Harbor Heights Elementary School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669002436` | Harbor Ridge Middle School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669002463` | Henderson Bay Alt High School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669001863` | Key Peninsula Middle School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669001862` | Kopachuck Middle School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669002007` | Minter Creek Elementary | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669000985` | Peninsula High School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669003760` | Pioneer Elementary School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669000986` | Purdy Elementary School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669003806` | Swift Water Elementary | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669000988` | Vaughn Elementary School | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530669002266` | Voyager Elementary | Peninsula School District | Green Ribbon | awards_recognition | stage1_excluded | arned federal recognition as 'Green Ribbon' schools in recognition of en... |
| `530682000999` | Hamilton Elementary | Port Angeles School District | Achievement Award (general) | awards_recognition | stage1_filtered_to_zero (no included) | SASCD and the 2015 Washington Achievement Award for High Progress.... |
| `530682000999` | Hamilton Elementary | Port Angeles School District | Blue Ribbon | awards_recognition | stage1_filtered_to_zero (no included) | ary was named a 2020 National Blue Ribbon School by the U.S. Department... |
| `530682000999` | Hamilton Elementary | Port Angeles School District | National Blue Ribbon | awards_recognition | stage1_filtered_to_zero (no included) | n Elementary was named a 2020 National Blue Ribbon School by the U.S. Department... |
| `530682000999` | Hamilton Elementary | Port Angeles School District | Washington Achievement Award | awards_recognition | stage1_filtered_to_zero (no included) | ward from WSASCD and the 2015 Washington Achievement Award for High Progress.... |
| `530696002340` | Frank Brouillet Elem | Puyallup School District | Dual immersion / dual language | programs | stage1_excluded | participates in district-wide dual language programs including Spanish-Du... |
| `530696001795` | Ridgecrest Elementary | Puyallup School District | Blue Ribbon | awards_recognition | stage1_excluded |  was recognized as a National Blue Ribbon School and has received nine ... |
| `530696001795` | Ridgecrest Elementary | Puyallup School District | National Blue Ribbon | awards_recognition | stage1_excluded | lementary was recognized as a National Blue Ribbon School and has received nine ... |
| `530723002564` | Dimmitt Middle School | Renton School District | International Baccalaureate | programs | stage1_excluded | ol has been authorized by the International Baccalaureate Organization (IBO) to ... |
| `530723001085` | Talbot Hill Elementary School | Renton School District | Achievement Award (general) | awards_recognition | stage1_excluded | chool received the Washington Achievement Award, which honors the top perform... |
| `530723001085` | Talbot Hill Elementary School | Renton School District | Washington Achievement Award | awards_recognition | stage1_excluded | lementary School received the Washington Achievement Award, which honors the top... |
| `530732001091` | Carmichael Middle School | Richland School District | Teacher of the Year | awards_recognition | stage1_excluded | ton State Middle School Music Teacher of the Year by the Washington Music Educa... |
| `530732001095` | Hanford High School | Richland School District | Teacher of the Year | awards_recognition | stage1_excluded | ion Association (JEA) and the Teacher of the Year Award at the 2024 All-America... |
| `530771001157` | B F Day Elementary School | Seattle School District No. 1 | Blue Ribbon | awards_recognition | stage1_excluded | received the Washington State Blue Ribbon school distinction in 1999 un... |
| `530771003390` | Cascadia Elementary | Seattle School District No. 1 | Blue Ribbon | awards_recognition | stage1_excluded | .S. Department of Education's Blue Ribbon Award in August 2025, recogni... |
| `530771001154` | Concord International School | Seattle School District No. 1 | Dual immersion / dual language | programs | stage1_excluded | rnational School with two-way dual language immersion in Spanish and Engl... |
| `530771001161` | Dunlap Elementary School | Seattle School District No. 1 | Achievement Award (general) | awards_recognition | stage0_dropped | eived an Excellence in Design Achievement award from School Planning & Manage... |
| `530771001171` | Garfield High School | Seattle School District No. 1 | Schools of Distinction | awards_recognition | stage1_excluded | n King County to receive the 'School of Distinction' award in 2007.... |
| `530771001171` | Garfield High School | Seattle School District No. 1 | State champion | programs | stage1_excluded | ict championship, and WIAA 3A State Championship in 2019, becoming the fir... |
| `530771001180` | Hamilton International Middle School | Seattle School District No. 1 | Schools of Distinction | awards_recognition | stage1_excluded |  was named a Washington State School of Distinction, an award presented to the t... |
| `530771003426` | Louisa Boren STEM K-8 | Seattle School District No. 1 | Schools of Distinction | awards_recognition | stage1_excluded | gnized as a Washington State 'School of Distinction' by Seattle Public Schools f... |
| `530771001212` | McClure Middle School | Seattle School District No. 1 | Schools of Distinction | awards_recognition | stage1_excluded | oximately 450) to receive the School of Distinction Award from The Center for Ed... |
| `530771001228` | Olympic Hills Elementary School | Seattle School District No. 1 | Schools of Distinction | awards_recognition | stage1_excluded |  in King County to receive a 'school of distinction' award from the Washington S... |
| `530771002347` | Thurgood Marshall Elementary | Seattle School District No. 1 | Blue Ribbon | awards_recognition | stage1_excluded | rded the prestigious National Blue Ribbon Schools designation by the U.... |
| `530771002347` | Thurgood Marshall Elementary | Seattle School District No. 1 | Blue Ribbon | leadership | stage1_excluded |  school received its National Blue Ribbon designation.... |
| `530771002347` | Thurgood Marshall Elementary | Seattle School District No. 1 | National Blue Ribbon | awards_recognition | stage1_excluded | y was awarded the prestigious National Blue Ribbon Schools designation by the U.... |
| `530771002347` | Thurgood Marshall Elementary | Seattle School District No. 1 | National Blue Ribbon | leadership | stage1_excluded |  when the school received its National Blue Ribbon designation.... |
| `530771001263` | West Woodland Elementary School | Seattle School District No. 1 | Schools of Distinction | awards_recognition | stage1_excluded |  first schools to receive the School of Distinction award from the Washington Of... |
| `530774001277` | Mary Purcell Elementary School | Sedro-Woolley School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) |  School was honored as a 2018 School of Distinction by the Northwest Educational... |
| `530804001330` | Mount Si High School | Snoqualmie Valley School District | State champion | awards_recognition | stage1_excluded | ol won the 4A Boys basketball state championship in 2024 with a 25-0 state... |
| `530816001353` | Orchard Heights Elementary | South Kitsap School District | International Baccalaureate | leadership | stage1_excluded | e school's drive to become an International Baccalaureate school.... |
| `530816001353` | Orchard Heights Elementary | South Kitsap School District | Schools of Distinction | awards_recognition | stage1_excluded | eights Elementary was named a School of Distinction Award winner by the Center f... |
| `530825001361` | Adams Elementary | Spokane School District | Achievement Award (general) | awards_recognition | stage1_excluded | ary is a five-time Washington Achievement Award earner.... |
| `530825001361` | Adams Elementary | Spokane School District | Washington Achievement Award | awards_recognition | stage1_excluded | ams Elementary is a five-time Washington Achievement Award earner.... |
| `530825001374` | Franklin Elementary | Spokane School District | Blue Ribbon | awards_recognition | stage1_excluded | mentary received the National Blue Ribbon Schools Award in 2004, recogn... |
| `530825001374` | Franklin Elementary | Spokane School District | National Blue Ribbon | awards_recognition | stage1_excluded | nklin Elementary received the National Blue Ribbon Schools Award in 2004, recogn... |
| `530825002366` | Moran Prairie Elementary | Spokane School District | Blue Ribbon | awards_recognition | stage1_excluded | rairie Elementary was named a Blue Ribbon school by the U.S. Department... |
| `530825003912` | Ruben Trejo Dual Language Academy | Spokane School District | Dual immersion / dual language | awards_recognition | stage1_excluded |  voted to officially name the dual language school 'Ruben Trejo Dual Lang... |
| `530825003912` | Ruben Trejo Dual Language Academy | Spokane School District | Dual immersion / dual language | programs | stage1_excluded | Ruben Trejo Dual Language Academy relocated from a shar... |
| `530825003912` | Ruben Trejo Dual Language Academy | Spokane School District | Dual immersion / dual language | other | in_final_narrative | Ruben Trejo Dual Language Academy was briefly closed in... |
| `530825001412` | Stevens Elementary | Spokane School District | Schools of Distinction | awards_recognition | stage1_excluded | tevens Elementary received a "School of Distinction" banner and recognition for ... |
| `530870001466` | Foss High School | Tacoma School District | International Baccalaureate | awards_recognition | stage1_excluded | Washington state to offer the International Baccalaureate (IB) program in 1982 a... |
| `530876001463` | Glacier Park Elementary | Tahoma School District | Green Ribbon | awards_recognition | stage1_excluded | tates Department of Education Green Ribbon Award winner for commitment t... |
| `530927000578` | Alki Middle School | Vancouver School District | Teacher of the Year | awards_recognition | stage1_excluded | teachers at Washington's 2009 Teacher of the Year ceremony and named Regional T... |
| `530927001557` | Columbia River High | Vancouver School District | International Baccalaureate | other | stage1_excluded | h School was authorized as an International Baccalaureate World School in 1994 a... |
| `530927001557` | Columbia River High | Vancouver School District | Magnet school | other | stage1_excluded | chool in 1994 and serves as a magnet school in Vancouver School District ... |
| `530927001558` | Dwight D Eisenhower Elementary | Vancouver School District | Schools of Distinction | awards_recognition | stage1_excluded | honored as a Washington state School of Distinction in October 2008.... |
| `530927001558` | Dwight D Eisenhower Elementary | Vancouver School District | Title I Distinguished | awards_recognition | stage1_excluded | nated as a 2008-2009 National Title I Distinguished School based on exceptional ... |
| `530927001564` | Harney Elementary School | Vancouver School District | Schools of Distinction | awards_recognition | stage1_excluded | arney Elementary received the School of Distinction Award for showing sustained ... |
| `530927001568` | Hough Elementary School | Vancouver School District | Achievement Award (general) | awards_recognition | stage1_excluded | lementary earned a Washington Achievement Award in April 2015, recognizing it... |
| `530927001568` | Hough Elementary School | Vancouver School District | Washington Achievement Award | awards_recognition | stage1_excluded | Hough Elementary earned a Washington Achievement Award in April 2015, recognizin... |
| `530927001576` | Martin Luther King Elementary | Vancouver School District | Title I Distinguished | awards_recognition | stage0_dropped |  King Elementary received the Title I Distinguished School Award, one of only fo... |
| `530927001580` | Peter S Ogden Elementary | Vancouver School District | Title I Distinguished | awards_recognition | stage1_excluded |  in Washington state to win a Title I Distinguished School Award for closing the... |
| `530927000638` | Roosevelt Elementary School | Vancouver School District | Title I Distinguished | awards_recognition | stage0_dropped | tary School received the 1998 Title I Distinguished School Award from the U.S. D... |
| `530927001583` | Sarah J Anderson Elementary | Vancouver School District | Dual immersion / dual language | programs | stage1_excluded | The district's first Dual Language programs began at Sarah J. An... |
| `530927002555` | Skyview High School | Vancouver School District | FIRST competition | programs | stage1_excluded | ew High School is home to two FIRST Robotics Competition teams: the 2811 S... |
| `530927002944` | Thomas Jefferson Middle School | Vancouver School District | Teacher of the Year | awards_recognition | stage1_excluded |  honored as Washington's 2009 Teacher of the Year and Regional Teacher of the Y... |
| `530927002508` | Vancouver School of Arts and Academics | Vancouver School District | Blue Ribbon | awards_recognition | stage1_excluded | zed as a No Child Left Behind Blue Ribbon School for 2005 by the U.S. D... |
| `530927002508` | Vancouver School of Arts and Academics | Vancouver School District | Teacher of the Year | awards_recognition | stage1_excluded | Washington state's 2012 Dance Teacher of the Year by the Washington Alliance fo... |
| `530939002492` | Preston Hall Middle School | Waitsburg School District | Achievement Award (general) | awards_recognition | stage1_filtered_to_zero (no included) | eived the Washington Academic Achievement Award. Waitsburg Elementary was nam... |
| `530939002492` | Preston Hall Middle School | Waitsburg School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) | tsburg Elementary was named a School of Distinction.... |
| `530939001596` | Waitsburg Elementary School | Waitsburg School District | Achievement Award (general) | awards_recognition | stage1_filtered_to_zero (no included) | eived the Washington Academic Achievement Award. Waitsburg Elementary was nam... |
| `530939001596` | Waitsburg Elementary School | Waitsburg School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) | tsburg Elementary was named a School of Distinction.... |
| `530939001597` | Waitsburg High School | Waitsburg School District | Achievement Award (general) | awards_recognition | stage1_filtered_to_zero (no included) | eived the Washington Academic Achievement Award. Waitsburg Elementary was nam... |
| `530939001597` | Waitsburg High School | Waitsburg School District | Schools of Distinction | awards_recognition | stage1_filtered_to_zero (no included) | tsburg Elementary was named a School of Distinction.... |
| `530969003769` | Spokane Valley High School | West Valley School District (Spokane) | Achievement Award (general) | awards_recognition | stage1_excluded |  has won the Washington State Achievement Award, Washington Designated Innova... |
| `530972001650` | Apple Valley Elementary | West Valley School District (Yakima) | Blue Ribbon | awards_recognition | stage1_filtered_to_zero (no included) | recognized as a 2023 National Blue Ribbon School</cite>. <cite index="1... |
| `530972001650` | Apple Valley Elementary | West Valley School District (Yakima) | National Blue Ribbon | awards_recognition | stage1_filtered_to_zero (no included) | kima was recognized as a 2023 National Blue Ribbon School</cite>. <cite index="1... |
| `530972003669` | West Valley Open Doors | West Valley School District (Yakima) | Career pathway | leadership | stage1_filtered_to_zero (no included) | , providing academic support, career pathways, case management, and mental... |
| `531011001686` | Barge-Lincoln Elementary School | Yakima School District | Dual immersion / dual language | awards_recognition | stage1_excluded |  from the state in academics, dual language instruction, and school clima... |
| `531011001689` | Davis High School | Yakima School District | State champion | awards_recognition | stage1_excluded | ool Pirates won the 2024 WIAA State Championship, defeating the Sumner Spa... |
| `531014002393` | Fort Stevens Elementary | Yelm School District | Schools of Distinction | awards_recognition | stage1_excluded | tevens Elementary was named a School of Distinction for the 2013-14 school year,... |
| `531014002393` | Fort Stevens Elementary | Yelm School District | Teacher of the Year | awards_recognition | stage1_excluded | ry, was honored as Elementary Teacher of the Year for the Yelm School District.... |

---

Diagnostic only. No data modified. No prompts modified. No further pipeline runs triggered.