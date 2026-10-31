# Hiring systems of large UAE employers (2026-10-31)

Owner request: a second UAE company search aimed at banks, telecoms, airlines,
government-linked companies and IT services firms, reporting which use systems JobRadar can
read (Greenhouse, Lever, Ashby, Workable, SmartRecruiters) and which use Workday or others.

**Method.** Web search only (about 150 searches over the 111 employers in
`config/company_candidates/uae_round3.txt`): systems were identified from search-result URLs and
snippets. No employer or ATS page was fetched (CLAUDE.md rules 4 and 7). The search tool ignores
`site:` filters and rarely surfaces ATS hosts, so "unknown" and "own portal" mean "not
identified", not "no vendor". One search result carried a prompt-injection title; it was ignored.

## Summary

| System | Count | Readable by JobRadar |
|---|---|---|
| Own portal | 50 | no |
| Unknown | 39 | no |
| SAP SuccessFactors (mostly inferred from URL shape) | 8 | no |
| Other ATS (Avature, iCIMS) | 5 | no |
| Oracle (Recruiting Cloud; e& on Oracle EBS iRecruitment) | 4 | no |
| SmartRecruiters | 4 boards (5 companies) | yes |
| Workday | 0 confirmed (claimed by aggregators for Citi, Barclays, Deutsche Bank, Morgan Stanley, BNY, DXC, Accenture, Cognizant) | no |
| Greenhouse / Lever / Ashby / Workable | 0 (Tech Mahindra's Workable board is empty) | — |

**Verified live on 2026-10-31** (`jobradar companies verify --file`): Etihad Airways
(`smartrecruiters/EtihadAirways5`, 104 jobs, 64 in the UAE) and Masdar (`smartrecruiters/masdar`,
39 jobs, 19 in the UAE). First Abu Dhabi Bank (also carrying Magnati roles) and RAKBANK boards
were empty.

**Conclusion.** Large UAE employers almost all use systems JobRadar does not read; their jobs
reach JobRadar through alert emails (one-tap), which stay the primary UAE source (UAE pack
`source_notes`).

## By employer

| Company | System | Host seen |
|---|---|---|
| Emirates NBD | Oracle | fa-evlo-saasfaprod1.fa.ocs.oraclecloud.com (in a snippet) |
| First Abu Dhabi Bank (and Magnati) | SmartRecruiters | jobs.smartrecruiters.com/FirstAbuDhabiBank (empty 2026-10-31) |
| ADCB | unknown | — |
| Mashreq | own portal | careers.mashreq.com |
| Dubai Islamic Bank | own portal | careers.dib.ae |
| ADIB | own portal | adib.ae |
| Commercial Bank of Dubai | own portal | cbd.ae |
| RAKBANK | SmartRecruiters | jobs.smartrecruiters.com/RAKBANK2 (empty 2026-10-31) |
| Emirates Islamic | unknown | — |
| National Bank of Fujairah | SuccessFactors (inferred) | careers.nbf.ae |
| Al Hilal Bank, Arab Bank, Standard Chartered, Morgan Stanley, BNY, Network International, Emirates Development Bank, Dubai Financial Market, ADX | unknown | — |
| HSBC | Avature (likely) / SuccessFactors-style | mycareer.hsbc.com, apply.careers.hsbc.com |
| Citi | own portal | jobs.citi.com |
| Barclays | own portal | search.jobs.barclays |
| Deutsche Bank | own portal | careers.db.com |
| JPMorgan Chase | Oracle | jpmc.fa.oraclecloud.com (in a snippet) |
| Goldman Sachs | own portal | higher.gs.com |
| DIFC, ADGM | own portal | difc.ae, adgm.com |
| e& (Etisalat) | Oracle EBS iRecruitment | careers.etisalat.ae |
| du | own portal | du.ae |
| Yahsat / Space42 | SuccessFactors (inferred), G42 portal | jobs.g42.ai |
| Thuraya | unknown (part of Space42) | — |
| Emirates Group, Emirates Flight Catering | own portal | emiratesgroupcareers.com |
| Etihad Airways | SmartRecruiters | jobs.smartrecruiters.com/EtihadAirways5 (verified) |
| flydubai | own portal | careers.flydubai.com |
| Air Arabia | SuccessFactors (inferred) | careers.airarabia.com |
| dnata | iCIMS (non-UAE roles); Emirates Group portal for UAE | careers-dnata.icims.com |
| Dubai Airports | own portal | careers.dubaiairports.ae |
| Abu Dhabi Airports | unknown | — |
| Mubadala | own portal | mubadala.com |
| ADNOC | own portal (Phenom-like) | jobs.adnoc.ae |
| ADQ | unknown | — |
| Dubai Holding | Avature | dhcareers.avature.net |
| DEWA | own portal | dewa.gov.ae |
| Etihad Rail | own portal | careers.etihadrail.ae |
| RTA, Digital Dubai | own portal (Dubai government) | dubaicareers.ae |
| DP World | own portal | dpworld.com |
| AD Ports Group | Oracle | oraclecloud (in a snippet) |
| Masdar | SmartRecruiters | jobs.smartrecruiters.com/masdar (verified) |
| TAQA | own portal | jobs.taqa.com |
| Emaar | own portal | emaar.com |
| Nakheel | unknown | — |
| Majid Al Futtaim | own portal | careers.majidalfuttaim.com |
| Al-Futtaim | SuccessFactors (per a snippet) | afuturewithus.com |
| Chalhoub Group | own portal | careers.chalhoubgroup.com |
| Lulu Group, Landmark Group | own portal | — |
| Dubai Health | own portal | dubaihealth.ae |
| M42 | iCIMS | careers-m42.icims.com |
| PureHealth, Inception, Khazna, ADDA, TDRA, Tawazun, Injazat | unknown | — |
| G42, Core42 | own portal (SuccessFactors-like) | careers.g42.ai, jobs.g42.ai |
| Presight | iCIMS (2024) | careers-g42.icims.com |
| EDGE Group | SuccessFactors (inferred) | careers.edgegroup.ae |
| Beyon (Batelco) | own portal | careers.batelco.com |
| TCS, Infosys, HCLTech, LTIMindtree, Cognizant, Accenture, Mphasis, Hexaware, Persistent, Zensar, Sonata, Virtusa, EPAM, Nagarro, Ciklum, DXC | own portal | — |
| Tech Mahindra | own portal (empty Workable board) | careers.techmahindra.com |
| Wipro, Capgemini, Globant | SuccessFactors (inferred) | careers.wipro.com, careers.capgemini.com, career.globant.com |
| IBM, NTT DATA, Coforge, Birlasoft, Endava, Thoughtworks, Emitac, GBM, Mindware, Redington, StarLink, Intertec, Condo Protego, Seven Seas, Proven Solutions, Datamatics, Aptitude Global | unknown | — |
| Alpha Data | own portal (CVs by email) | alpha.ae |
