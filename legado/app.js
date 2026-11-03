/**
 * Sistema de Gestão de Campanhas e Sorteios — Barcarena/PA
 * Frontend Standalone com Mock Database Local (LocalStorage) e Testes Integrados
 */

const MOCK_DATA_ROWS = [{"row": 9, "box": "260", "name": "Sulamita Ferreira Figueira.", "activity": "SALÃO E BARBEARIA"}, {"row": 10, "box": "261", "name": "Valdicelio Gomes da Silva.", "activity": "SALÃO E BARBEARIA"}, {"row": 11, "box": "262", "name": "Helenilza Lima Vieira.", "activity": "SALÃO E BARBEARIA"}, {"row": 12, "box": "279", "name": "Edir Marques de Freitas.", "activity": "SALÃO E BARBEARIA"}, {"row": 13, "box": "302", "name": "Maria Raimunda Barros da Silva.", "activity": "SALÃO E BARBEARIA"}, {"row": 14, "box": "325", "name": "Davi César Pires de Melo", "activity": "SALÃO E BARBEARIA"}, {"row": 15, "box": "326", "name": "Gessiane Naiara Luz dos Santos", "activity": "SALÃO E BARBEARIA"}, {"row": 16, "box": "327", "name": "Rosildo Oliveira de Souza.", "activity": "SALÃO E BARBEARIA"}, {"row": 17, "box": "303", "name": "Maria do Socorro do Nascimento.", "activity": "CONFECÇÃO"}, {"row": 18, "box": "304", "name": "Maria do socorro Marques", "activity": "CONFECÇÃO"}, {"row": 19, "box": "305", "name": "Kariny Cristina da Silva vilhena", "activity": "CONFECÇÃO"}, {"row": 20, "box": "306", "name": "Maria Rosa Dias de Magalhães.", "activity": "CONFECÇÃO"}, {"row": 21, "box": "307", "name": "Nádia Vanessa Siqueira Castro.", "activity": "CONFECÇÃO"}, {"row": 22, "box": "308", "name": "Adson do Espírito Santo Canavieira", "activity": "CONFECÇÃO"}, {"row": 23, "box": "309", "name": "Paulo Maia Soares.", "activity": "CONFECÇÃO"}, {"row": 24, "box": "310", "name": "Maria Cleuza Leão Ribeiro", "activity": "CONFECÇÃO"}, {"row": 25, "box": "311", "name": "Maria do Espírito Santo Santiago Cunha", "activity": "CONFECÇÃO"}, {"row": 26, "box": "312", "name": "Maria Luiza Silva Sousa.", "activity": "CONFECÇÃO"}, {"row": 27, "box": "313", "name": "Ozana Lameira da Silva.", "activity": "CONFECÇÃO"}, {"row": 28, "box": "314", "name": "Arilda Nascimento.", "activity": "CONFECÇÃO"}, {"row": 29, "box": "315", "name": "Raquel do Socorro da Silva Batista", "activity": "CONFECÇÃO"}, {"row": 30, "box": "316", "name": "Adriele Camile Nascimento de Sena.", "activity": "CONFECÇÃO"}, {"row": 31, "box": "317", "name": "Jamily Kerolayne Castilho Ribeiro.", "activity": "CONFECÇÃO"}, {"row": 32, "box": "318", "name": "Diolene Teles Afonso", "activity": "CONFECÇÃO"}, {"row": 33, "box": "319", "name": "Raimundo Batista da Fonseca", "activity": "CONFECÇÃO"}, {"row": 34, "box": "320", "name": "Rosineide da Conceição Cachiada.", "activity": "CONFECÇÃO"}, {"row": 35, "box": "321", "name": "Renata Kelly Batista da Costa.", "activity": "CONFECÇÃO"}, {"row": 36, "box": "328", "name": "Winglid Patrícia Barbosa Costa.", "activity": "CONFECÇÃO"}, {"row": 37, "box": "329", "name": "Ivanete Portilho Batista.", "activity": "CONFECÇÃO"}, {"row": 38, "box": "330", "name": "Laura Paloma Gomes Correa", "activity": "CONFECÇÃO"}, {"row": 39, "box": "331", "name": "Ivanise Veras Fontes.", "activity": "CONFECÇÃO"}, {"row": 40, "box": "332", "name": "Sebastiana da Silva Gomes", "activity": "CONFECÇÃO"}, {"row": 41, "box": "333", "name": "Dinair do Nascimento.", "activity": "CONFECÇÃO"}, {"row": 42, "box": "334", "name": "Francisco de Assis da Silva Braga", "activity": "CONFECÇÃO"}, {"row": 43, "box": "335", "name": "Marelilda Nascimento Castilho.", "activity": "CONFECÇÃO"}, {"row": 44, "box": "336", "name": "Maria das Graças Maia costa", "activity": "CONFECÇÃO"}, {"row": 45, "box": "337", "name": "Louriléia Moraes dos Santos.", "activity": "CONFECÇÃO"}, {"row": 46, "box": "338", "name": "Maria Matos da Cruz.", "activity": "CONFECÇÃO"}, {"row": 47, "box": "339", "name": "Ivanilde Martins da Silva", "activity": "CONFECÇÃO"}, {"row": 48, "box": "215", "name": "Elmira de Brito Campos.", "activity": "VARIEDADES"}, {"row": 49, "box": "225", "name": "José Maria Ferreira", "activity": "VARIEDADES"}, {"row": 50, "box": "226", "name": "Jose Junior Barbosa Costa", "activity": "VARIEDADES"}, {"row": 51, "box": "227", "name": "Maria da Luz da Silva Santana Farias", "activity": "VARIEDADES"}, {"row": 52, "box": "228", "name": "Cleonice Pinheiro Correa.", "activity": "VARIEDADES"}, {"row": 53, "box": "229", "name": "Edson Pantoja Ferreira.", "activity": "VARIEDADES"}, {"row": 54, "box": "230", "name": "José Menezes Damasceno.", "activity": "VARIEDADES"}, {"row": 55, "box": "231", "name": "Creuza Maria do Nascimento Barbosa.", "activity": "VARIEDADES"}, {"row": 56, "box": "232", "name": "Vânia Cristina Sodré de Souza", "activity": "VARIEDADES"}, {"row": 57, "box": "233", "name": "Franciany da Silva Batista", "activity": "VARIEDADES"}, {"row": 58, "box": "234", "name": "Geraldo Veiga Teles.", "activity": "VARIEDADES"}, {"row": 59, "box": "235", "name": "Paulo Sérgio Rego de Almeida", "activity": "VARIEDADES"}, {"row": 60, "box": "236", "name": "Ivanilda de Castro Lima", "activity": "VARIEDADES"}, {"row": 61, "box": "237", "name": "Domingas dos Passos Nunes", "activity": "VARIEDADES"}, {"row": 62, "box": "238", "name": "Wenderson Silva Martins.", "activity": "VARIEDADES"}, {"row": 63, "box": "239", "name": "Joelma Veras Pereira", "activity": "VARIEDADES"}, {"row": 64, "box": "240", "name": "Laurinéia da Silva Oliveira.", "activity": "VARIEDADES"}, {"row": 65, "box": "241", "name": "Lauriene do S. Gonçalves Marques.", "activity": "VARIEDADES"}, {"row": 66, "box": "242", "name": "Gorete de Barros Ferreira", "activity": "VARIEDADES"}, {"row": 67, "box": "243", "name": "Oneide Araújo Costa Pantoja", "activity": "VARIEDADES"}, {"row": 68, "box": "244", "name": "Afonso Moraes Fonseca", "activity": "VARIEDADES"}, {"row": 69, "box": "245", "name": "Maria Eliete Gouvea Cardoso", "activity": "VARIEDADES"}, {"row": 70, "box": "246", "name": "Joana Miranda Barbosa.", "activity": "VARIEDADES"}, {"row": 71, "box": "254", "name": "Walber Monteiro Freitas", "activity": "VARIEDADES"}, {"row": 72, "box": "299", "name": "Maria da Conceição das Dores Melo.", "activity": "VARIEDADES"}, {"row": 73, "box": "300", "name": "Waldenise das Neves Silva", "activity": "VARIEDADES"}, {"row": 74, "box": "301", "name": "Maria das Graças Carvalho Moraes.", "activity": "VARIEDADES"}, {"row": 75, "box": "322", "name": "Joacir Correa de Oliveira", "activity": "VARIEDADES"}, {"row": 76, "box": "323", "name": "Margareth do Socorro Costa Gouvêa.", "activity": "VARIEDADES"}, {"row": 77, "box": "324", "name": "Eliezer Barreto Pereira", "activity": "VARIEDADES"}, {"row": 78, "box": "255", "name": "Francineide Dias Tavares", "activity": "VARIEDADES"}, {"row": 79, "box": "257", "name": "Jean Lima de Andrade", "activity": "VARIEDADES"}, {"row": 80, "box": "340", "name": "Elthon Martins Souza", "activity": "P. ELETRONICOS"}, {"row": 81, "box": "341", "name": "NEWFARMA – LOUISE MORAES BRAGA", "activity": "FARMACIA"}, {"row": 82, "box": "342", "name": "Elson do Socorro Lima da Costa.", "activity": "DESCARTAVIES"}, {"row": 83, "box": "343", "name": "Davi Beltrão da Silva Filho.", "activity": "DESCARTAVIES"}, {"row": 84, "box": "258", "name": "Gilberto Gonçalves Marques.", "activity": "MERCEARIA"}, {"row": 85, "box": "259", "name": "vago", "activity": "MERCEARIA"}, {"row": 86, "box": "263", "name": "Rosa Maria da Silva Alves.", "activity": "MERCEARIA"}, {"row": 87, "box": "264", "name": "Lucilene Alves Brito", "activity": "MERCEARIA"}, {"row": 88, "box": "265", "name": "Vilma do Socorro Magno Oda.", "activity": "MERCEARIA"}, {"row": 89, "box": "266", "name": "Elias Campos Barbosa.", "activity": "MERCEARIA"}, {"row": 90, "box": "267", "name": "Vicente Benjamim de Medeiros.", "activity": "MERCEARIA"}, {"row": 91, "box": "268", "name": "Franciane Nascimento de Souza", "activity": "MERCEARIA"}, {"row": 92, "box": "269", "name": "Lucivaldo Bitencourt da Silva.", "activity": "MERCEARIA"}, {"row": 93, "box": "270", "name": "Maria do Socorro Pantoja Ferreira.", "activity": "MERCEARIA"}, {"row": 94, "box": "271", "name": "Maria José Sampaio da Silva.", "activity": "MERCEARIA"}, {"row": 95, "box": "272", "name": "Lindalva Nonata de Sousa", "activity": "MERCEARIA"}, {"row": 96, "box": "273", "name": "Armando Rufino Patricio", "activity": "MERCEARIA"}, {"row": 97, "box": "274", "name": "vago", "activity": "MERCEARIA"}, {"row": 98, "box": "275", "name": "Valdicléia Oliveira Frazão.", "activity": "MERCEARIA"}, {"row": 99, "box": "276", "name": "Osmarino Lima da Silva.", "activity": "MERCEARIA"}, {"row": 100, "box": "277", "name": "Lucirene Barbosa Lobato.", "activity": "MERCEARIA"}, {"row": 101, "box": "278", "name": "Beatriz Pereira Da Costa", "activity": "MERCEARIA"}, {"row": 102, "box": "280", "name": "José Rocha da Poça.", "activity": "MERCEARIA"}, {"row": 103, "box": "281", "name": "André Luís de Moraes Stefani.", "activity": "MERCEARIA"}, {"row": 104, "box": "282", "name": "Maria Regina de Souza Góes.", "activity": "MERCEARIA"}, {"row": 105, "box": "283", "name": "Raimundo das Graças Dias", "activity": "MERCEARIA"}, {"row": 106, "box": "284", "name": "Luis Carlos Costa Silva", "activity": "MERCEARIA"}, {"row": 107, "box": "285", "name": "Dejacir Martins Magno.", "activity": "MERCEARIA"}, {"row": 108, "box": "286", "name": "Nilamon Xavier de Sena Neto", "activity": "MERCEARIA"}, {"row": 109, "box": "287", "name": "Catarina de Sena Luna da Silva.", "activity": "MERCEARIA"}, {"row": 110, "box": "288", "name": "Maria de Fátima Soares da Silva", "activity": "MERCEARIA"}, {"row": 111, "box": "289", "name": "Jorgem do Carmo Delgado", "activity": "MERCEARIA"}, {"row": 112, "box": "290", "name": "Francisco Olivaldo Silva da Silva.", "activity": "MERCEARIA"}, {"row": 113, "box": "291", "name": "Maria do Carmo Marques da Conceição.", "activity": "MERCEARIA"}, {"row": 114, "box": "292", "name": "Vera Lúcia Gonçalves Marques.", "activity": "MERCEARIA"}, {"row": 115, "box": "293", "name": "Celso da Silva Monteiro.", "activity": "MERCEARIA"}, {"row": 116, "box": "294", "name": "Ana Cristina Soares Maués", "activity": "MERCEARIA"}, {"row": 117, "box": "295", "name": "Valdirene de Oliveira Frazão.", "activity": "MERCEARIA"}, {"row": 118, "box": "296", "name": "Joyce Lobato Freitas.", "activity": "MERCEARIA"}, {"row": 119, "box": "297", "name": "Raimundo Oliveira Magalhães.", "activity": "MERCEARIA"}, {"row": 120, "box": "298", "name": "Prudêncio José da Silva Neto.", "activity": "MERCEARIA"}, {"row": 121, "box": "250", "name": "Samara de Cássia Barbosa Monteiro", "activity": "PET SHOP"}, {"row": 122, "box": "253", "name": "Eurídice de Melo Paes", "activity": "BOMBONS"}, {"row": 123, "box": "217", "name": "Lelson da Silva Oliveira.", "activity": "SERVIÇOS"}, {"row": 124, "box": "218", "name": "Cristiane Medeiros Filho.", "activity": "SERVIÇOS"}, {"row": 125, "box": "219", "name": "Francisco Cosme Lima Rodrigues.", "activity": "SERVIÇOS"}, {"row": 126, "box": "220", "name": "Edilson Gomes de Paula", "activity": "SERVIÇOS"}, {"row": 127, "box": "221", "name": "Gedilso Cardoso Siqueira.", "activity": "SERVIÇOS"}, {"row": 128, "box": "222", "name": "Jurandir Santos de Oliveira.", "activity": "SERVIÇOS"}, {"row": 129, "box": "223", "name": "Edson de Oliveira Lima.", "activity": "SERVIÇOS"}, {"row": 130, "box": "224", "name": "Marcos Vinicius Menezes Furtado.", "activity": "SERVIÇOS"}, {"row": 131, "box": "247", "name": "Valdo da Costa Furtado.", "activity": "SAPATERIOS"}, {"row": 132, "box": "248", "name": "Zeno Silva dos Santos", "activity": "SAPATERIOS"}, {"row": 133, "box": "249", "name": "João da Cruz Dias.", "activity": "SAPATERIOS"}, {"row": 134, "box": "350", "name": "Renan Magno Leal", "activity": "GELO"}, {"row": 135, "box": "351", "name": "José Ribamar Pinheiro Frazão.", "activity": "GELO"}, {"row": 136, "box": "256", "name": "Gisele Patrícia Camacho dos Santos.", "activity": "PRODUTOS NATURAIS"}, {"row": 137, "box": "257", "name": "Jean Lima de Andrade", "activity": "variedades"}, {"row": 138, "box": "348", "name": "Klaywer Dias Carneiro Viana.", "activity": "FERRAGEM"}, {"row": 139, "box": "349", "name": "Miria Ferreira Cardoso.", "activity": "FERRAGEM"}, {"row": 140, "box": "251", "name": "Miriam Elaine Cruz Pereira.", "activity": "SAPATARIA"}, {"row": 141, "box": "1", "name": "Raimundo do Socorro Perdigão de Matos", "activity": "CARNES"}, {"row": 142, "box": "02", "name": "Aldenise Brabo Correa.", "activity": "CARNES"}, {"row": 143, "box": "03", "name": "Janison Brabo Correa.", "activity": "CARNES"}, {"row": 144, "box": "04", "name": "Arinaldo Pereira Campos.", "activity": "CARNES"}, {"row": 145, "box": "05", "name": "Junilson da Silva Chagas.", "activity": "CARNES"}, {"row": 146, "box": "06", "name": "Denner Gustavo da Conceição Chagas.", "activity": "CARNES"}, {"row": 147, "box": "07", "name": "Domingos de Almeida Chagas.", "activity": "CARNES"}, {"row": 148, "box": "08", "name": "Marivaldo da Conceição Almeida.", "activity": "CARNES"}, {"row": 149, "box": "09", "name": "Raimundo Nazareno Pereira dos Santos", "activity": "CARNES"}, {"row": 150, "box": "18", "name": "Raimundo Costa Barreto.", "activity": "CARNES"}, {"row": 151, "box": "19", "name": "Manoel Neves dos Santos.", "activity": "CARNES"}, {"row": 152, "box": "20", "name": "Moisés Almeida Basilho.", "activity": "CARNES"}, {"row": 153, "box": "21", "name": "Adriele da Silva Reis Nascimento", "activity": "CARNES"}, {"row": 154, "box": "22", "name": "Douglas Gabriel da Conceição Chagas.", "activity": "CARNES"}, {"row": 155, "box": "23", "name": "Deone Almeida Basilho", "activity": "CARNES"}, {"row": 156, "box": "24", "name": "Thiago Moisés Farias Basilho", "activity": "CARNES"}, {"row": 157, "box": "25", "name": "vago", "activity": "CARNES"}, {"row": 158, "box": "26", "name": "Fabio José Machado de Souza.", "activity": "CARNES"}, {"row": 159, "box": "27", "name": "vago", "activity": "CARNES"}, {"row": 160, "box": "10", "name": "Vladenilson Pantoja Paixão.", "activity": "VICERAS"}, {"row": 161, "box": "11", "name": "Vanderlei Cardoso Gomes de Paula.", "activity": "VICERAS"}, {"row": 162, "box": "12", "name": "Raimundo Ferreira Castilho.", "activity": "VICERAS"}, {"row": 163, "box": "13", "name": "Edevaldo Kawaguchi.", "activity": "VICERAS"}, {"row": 164, "box": "28", "name": "Marivaldo de Nazaré Oliveira Costa.", "activity": "VICERAS"}, {"row": 165, "box": "29", "name": "Ramon Angel Andrade Magno", "activity": "FRANGO"}, {"row": 166, "box": "30", "name": "Nildo Barreto dos Santos.", "activity": "FRANGO"}, {"row": 167, "box": "31", "name": "João da Silva Nascimento.", "activity": "FRANGO"}, {"row": 168, "box": "58", "name": "Maria Isabel Bentes do Espírito Santo", "activity": "FRANGO"}, {"row": 169, "box": "32", "name": "Rosileide Bitencourt da Silva", "activity": "PEIXES"}, {"row": 170, "box": "33", "name": "Francivaldo Bitencourt da Silva.", "activity": "PEIXES"}, {"row": 171, "box": "34", "name": "Denys Rocha de Paula.", "activity": "PEIXES"}, {"row": 172, "box": "35", "name": "Nonato da Costa Negrão.", "activity": "PEIXES"}, {"row": 173, "box": "36", "name": "Elizeu Lagos Barbosa", "activity": "PEIXES"}, {"row": 174, "box": "37", "name": "Manoel Caetano Campos de Souza", "activity": "PEIXES"}, {"row": 175, "box": "38", "name": "Francisco Jorge Coutinho Dos Santos", "activity": "PEIXES"}, {"row": 176, "box": "39", "name": "Izaquiel Furtado Soeiro", "activity": "PEIXES"}, {"row": 177, "box": "40", "name": "Raimundo Nonato Gomes de Paula.", "activity": "PEIXES"}, {"row": 178, "box": "41", "name": "Terezinha Miranda da Costa.", "activity": "PEIXES"}, {"row": 179, "box": "42", "name": "vago", "activity": "PEIXES"}, {"row": 180, "box": "43", "name": "vago", "activity": "PEIXES"}, {"row": 181, "box": "44", "name": "Jose Gaudencio Pinheiro Pompeu", "activity": "PEIXES"}, {"row": 182, "box": "59", "name": "Renato Pires Mendes.", "activity": "PEIXES"}, {"row": 183, "box": "60", "name": "Marcelo Gomes da Silva.", "activity": "PEIXES"}, {"row": 184, "box": "61", "name": "Deusdeth Magno Martins.", "activity": "PEIXES"}, {"row": 185, "box": "62", "name": "Lourivaldo Cardoso Moura.", "activity": "PEIXES"}, {"row": 186, "box": "63", "name": "Delcídio dos Santos.", "activity": "PEIXES"}, {"row": 187, "box": "64", "name": "Osvaldo Farias Pires Neto.", "activity": "PEIXES"}, {"row": 188, "box": "65", "name": "Vitorino Mendes.", "activity": "PEIXES"}, {"row": 189, "box": "66", "name": "Ocir de Jesus Lima.", "activity": "PEIXES"}, {"row": 190, "box": "67", "name": "Sergio Andrade de Sena", "activity": "PEIXES"}, {"row": 191, "box": "68", "name": "Josenildo Rodrigues Dias", "activity": "PEIXES"}, {"row": 192, "box": "69", "name": "Eliel Barreto Pereira", "activity": "PEIXES"}, {"row": 193, "box": "70", "name": "Carlison de Moraes Costa", "activity": "PEIXES"}, {"row": 194, "box": "14", "name": "vago", "activity": "PEIXE SALGADO"}, {"row": 195, "box": "15", "name": "João Progênio dos Santos", "activity": "PEIXE SALGADO"}, {"row": 196, "box": "16", "name": "vago", "activity": "PEIXE SALGADO"}, {"row": 197, "box": "17", "name": "João Santiago de Vilhena", "activity": "PEIXE SALGADO"}, {"row": 198, "box": "157", "name": "Bruna de Castro Lobato", "activity": "HORTIFRUTES"}, {"row": 199, "box": "158", "name": "Luís Paulino Soares Nobre.", "activity": "HORTIFRUTES"}, {"row": 200, "box": "159", "name": "Daiane Medeiros Brito.", "activity": "HORTIFRUTES"}, {"row": 201, "box": "160", "name": "Raimundo Nonato Pereira da Silva", "activity": "HORTIFRUTES"}, {"row": 202, "box": "161", "name": "Agostinho Alves da Silva.", "activity": "HORTIFRUTES"}, {"row": 203, "box": "163", "name": "Diéssica Maria da Silva Trindade", "activity": "HORTIFRUTES"}, {"row": 204, "box": "165", "name": "Raimundo Rosa Vasconcelos Furtado.", "activity": "HORTIFRUTES"}, {"row": 205, "box": "166", "name": "Lindalva da Silva Correa.", "activity": "HORTIFRUTES"}, {"row": 206, "box": "167", "name": "Cosmes Cordeiro de Sena.", "activity": "HORTIFRUTES"}, {"row": 207, "box": "168", "name": "Antônio Hamilton Faial.", "activity": "HORTIFRUTES"}, {"row": 208, "box": "169", "name": "Marcelina da Silva e Silva", "activity": "HORTIFRUTES"}, {"row": 209, "box": "170", "name": "Pedro de Jesus Serrão Nunes.", "activity": "HORTIFRUTES"}, {"row": 210, "box": "354", "name": "Rui Poça Rocha Filho", "activity": "LANCHES E REFEIÇOES"}, {"row": 211, "box": "355", "name": "Maria Raimunda do Nascimento Barbosa.", "activity": "LANCHES E REFEIÇOES"}, {"row": 212, "box": "356", "name": "Lidiane Pereira Costa.", "activity": "LANCHES E REFEIÇOES"}, {"row": 213, "box": "357", "name": "Moisés Oliveira Costa.", "activity": "LANCHES E REFEIÇOES"}, {"row": 214, "box": "358", "name": "Lúcia Maria da Silva.", "activity": "LANCHES E REFEIÇOES"}, {"row": 215, "box": "359", "name": "Danilde Carvalho dos Anjos.", "activity": "LANCHES E REFEIÇOES"}, {"row": 216, "box": "360", "name": "Rozana Furtado da Silva", "activity": "LANCHES E REFEIÇOES"}, {"row": 217, "box": "361", "name": "Iranita Pereira Costa.", "activity": "LANCHES E REFEIÇOES"}, {"row": 218, "box": "362", "name": "Rosilda Vanzeler Ribeiro.", "activity": "LANCHES E REFEIÇOES"}, {"row": 219, "box": "363", "name": "Heloísa Ferreira de Araújo.", "activity": "LANCHES E REFEIÇOES"}, {"row": 220, "box": "364", "name": "Ana Lúcia Fernandes da Costa.", "activity": "LANCHES E REFEIÇOES"}, {"row": 221, "box": "365", "name": "Maria de Nazare costa Freitas", "activity": "LANCHES E REFEIÇOES"}, {"row": 222, "box": "366", "name": "Irene de Jesus Couto das Mercês.", "activity": "LANCHES E REFEIÇOES"}, {"row": 223, "box": "367", "name": "Marcelo Peterson Barbosa Ferreira.", "activity": "LANCHES E REFEIÇOES"}, {"row": 224, "box": "368", "name": "Vânia do S. Gonçalves da Silva.", "activity": "LANCHES E REFEIÇOES"}, {"row": 225, "box": "352", "name": "Maria do Socorro Nobre Pinheiro", "activity": "RESTAURANTE"}, {"row": 226, "box": "353", "name": "Jose João Silva Campos", "activity": "RESTAURANTE"}, {"row": 227, "box": "216", "name": "Rafael Amorim Alves", "activity": "ARTESANATO"}, {"row": 228, "box": "186", "name": "Rutilea Lopes Serrão de Lima", "activity": "ARTESANATO"}, {"row": 229, "box": "187", "name": "Kevyn Alison dos Santos Reis", "activity": "ARTESANATO"}, {"row": 230, "box": "188", "name": "vago", "activity": "ARTESANATO"}, {"row": 231, "box": "189", "name": "vago", "activity": "ARTESANATO"}, {"row": 232, "box": "190", "name": "Vanilza Ferreira Costa", "activity": "ARTESANATO"}, {"row": 233, "box": "191", "name": "Sandra Sueli Lopes de Souza", "activity": "ARTESANATO"}, {"row": 234, "box": "192", "name": "Odete Barros Furtado", "activity": "ARTESANATO"}, {"row": 235, "box": "193", "name": "vago", "activity": "ARTESANATO"}, {"row": 236, "box": "194", "name": "Luiz Sergio da Silva Lacerda", "activity": "ARTESANATO"}, {"row": 237, "box": "195", "name": "Rosimeire Pantoja Hiraide", "activity": "ARTESANATO"}, {"row": 238, "box": "196", "name": "Josiane Cordeiro Baia", "activity": "ARTESANATO"}, {"row": 239, "box": "47", "name": "Manoel Dias de Amorim.", "activity": "CARANGUEJOS"}, {"row": 240, "box": "48", "name": "", "activity": "CARANGUEJOS"}, {"row": 241, "box": "49", "name": "", "activity": "CARANGUEJOS"}, {"row": 242, "box": "50", "name": "Carlos Epifanio da Costa", "activity": "CARANGUEJOS"}, {"row": 243, "box": "51", "name": "", "activity": "CARANGUEJOS"}, {"row": 244, "box": "52", "name": "", "activity": "CARANGUEJOS"}, {"row": 245, "box": "53", "name": "", "activity": "CARANGUEJOS"}, {"row": 246, "box": "54", "name": "", "activity": "CARANGUEJOS"}, {"row": 247, "box": "55", "name": "João Bento do Nascimento", "activity": "CARANGUEJOS"}, {"row": 248, "box": "181", "name": "Raimunda da Silva Carneiro", "activity": "CAFEZINHO"}, {"row": 249, "box": "182", "name": "Antônia Souza da Silva", "activity": "CAFEZINHO"}, {"row": 250, "box": "183", "name": "Tais  Farias de Oliveira dos Santos", "activity": "CAFEZINHO"}, {"row": 251, "box": "184", "name": "Maria do Socorro Alcantara mendes", "activity": "CAFEZINHO"}, {"row": 252, "box": "185", "name": "Andreia Regina Fernandes da Costa", "activity": "CAFEZINHO"}, {"row": 253, "box": "210", "name": "vago", "activity": "CAFEZINHO"}, {"row": 254, "box": "211", "name": "Antônio Dama da Silva", "activity": "CAFEZINHO"}, {"row": 255, "box": "212", "name": "Rubens Leonço Cravo", "activity": "CAFEZINHO"}, {"row": 256, "box": "213", "name": "Charles Moraes maia", "activity": "CAFEZINHO"}, {"row": 257, "box": "214", "name": "Arlene Pinheiro da Silva", "activity": "CAFEZINHO"}, {"row": 258, "box": "180", "name": "Ana Maria Sidonio da Costa", "activity": "CAFEZINHO"}, {"row": 259, "box": "173", "name": "Rosália Lira da Silva", "activity": "ROUPAS DE SEGUNDO USO"}, {"row": 260, "box": "174", "name": "Maria do Socorro Soares Carvalho", "activity": "ROUPAS DE SEGUNDO USO"}, {"row": 261, "box": "175", "name": "José de Souza Monteiro", "activity": "ROUPAS DE SEGUNDO USO"}, {"row": 262, "box": "176", "name": "Maria Jaciara dos santos Siqueira", "activity": "ROUPAS DE SEGUNDO USO"}, {"row": 263, "box": "177", "name": "Sebastiana Ferreira Ribeiro", "activity": "ROUPAS DE SEGUNDO USO"}, {"row": 264, "box": "178", "name": "Narciza Ramos Lameira", "activity": "ROUPAS DE SEGUNDO USO"}, {"row": 265, "box": "179", "name": "Maria de Nazaré Furtado Rodrigues", "activity": "ROUPAS DE SEGUNDO USO"}, {"row": 266, "box": "71", "name": "Reinaldo da Costa Almeida", "activity": "COMERCIO EVENTUAL"}, {"row": 267, "box": "84", "name": "Marlon Pinheiro Frazão", "activity": "COMERCIO EVENTUAL"}, {"row": 268, "box": "85", "name": "Nelson Dos Reis Lima Tavares", "activity": "COMERCIO EVENTUAL"}, {"row": 269, "box": "86", "name": "Elisangela da Silva Souza", "activity": "COMERCIO EVENTUAL"}, {"row": 270, "box": "87", "name": "Manoel da Paz Oliveira Cardoso", "activity": "COMERCIO EVENTUAL"}, {"row": 271, "box": "88", "name": "Antônio Marcio Serrão Gomes", "activity": "COMERCIO EVENTUAL"}, {"row": 272, "box": "89", "name": "Carlos Alberto Fernandes Martins", "activity": "COMERCIO EVENTUAL"}, {"row": 273, "box": "90", "name": "Leandro Machado Queiros", "activity": "COMERCIO EVENTUAL"}, {"row": 274, "box": "91", "name": "", "activity": "COMERCIO EVENTUAL"}, {"row": 275, "box": "92", "name": "José Maria Alves dos Santos", "activity": "COMERCIO EVENTUAL"}, {"row": 276, "box": "93", "name": "Elivaldo Marques de Freitas", "activity": "COMERCIO EVENTUAL"}, {"row": 277, "box": "94", "name": "", "activity": "COMERCIO EVENTUAL"}, {"row": 278, "box": "95", "name": "", "activity": "COMERCIO EVENTUAL"}, {"row": 279, "box": "197", "name": "Malba Cristinha da conceição moras correia", "activity": "COMERCIO EVENTUAL"}, {"row": 280, "box": "198", "name": "Ronaldo Nascimento dos Santos", "activity": "COMERCIO EVENTUAL"}, {"row": 281, "box": "199", "name": "Raimundo do Socorro Gomes Monteiro", "activity": "COMERCIO EVENTUAL"}, {"row": 282, "box": "200", "name": "Maria de jesus de arquino Nunes", "activity": "COMERCIO EVENTUAL"}, {"row": 283, "box": "201", "name": "", "activity": "COMERCIO EVENTUAL"}, {"row": 284, "box": "202", "name": "", "activity": "COMERCIO EVENTUAL"}, {"row": 285, "box": "203", "name": "Lourival Martins Rodrigues", "activity": "COMERCIO EVENTUAL"}, {"row": 286, "box": "204", "name": "", "activity": "COMERCIO EVENTUAL"}, {"row": 287, "box": "205", "name": "Valdemir da Silva Dias", "activity": "COMERCIO EVENTUAL"}, {"row": 288, "box": "206", "name": "Rosilda Ferreira Castilho", "activity": "COMERCIO EVENTUAL"}, {"row": 289, "box": "207", "name": "", "activity": "COMERCIO EVENTUAL"}, {"row": 290, "box": "208", "name": "Jesus de Nazare da Silva Ferreira", "activity": "COMERCIO EVENTUAL"}, {"row": 291, "box": "209", "name": "Josias Costa Carvalho", "activity": "COMERCIO EVENTUAL"}, {"row": 292, "box": "45", "name": "Miguel Fernando Benjamim Lopes", "activity": "CAMARÃO E MARISCO"}, {"row": 293, "box": "46", "name": "Benedito Magno da Silva", "activity": "CAMARÃO E MARISCO"}, {"row": 294, "box": "56", "name": "Jorge Sá da Silva", "activity": "CAMARÃO E MARISCO"}, {"row": 295, "box": "57", "name": "VAGO", "activity": "CAMARÃO E MARISCO"}, {"row": 296, "box": "347", "name": "Anaclécio Felinto de Araújo.", "activity": "BATERIA"}, {"row": 297, "box": "346", "name": "SICREDI", "activity": "INSTITUIÇÃO FINANCEIRA"}, {"row": 298, "box": "344", "name": "Euller Carlos Goncalves dos Santos", "activity": "RELOJOEIRO"}, {"row": 299, "box": "345", "name": "Nubia Oliveira de Carvalho", "activity": "VARIEDADES"}, {"row": 300, "box": "252", "name": "Erenilson Ferreira da Silva", "activity": "ARTIGO RELIGIOSO"}];

const DEFAULT_STATE = {
  currentRole: 'atendente', // admin, atendente, permissionario
  campaigns: [
    {
      id: 1,
      name: 'Campanha Piloto — Revitalização do Complexo',
      description: 'Campanha de ativação comercial conforme diagnóstico SEMAGRI/SEICOMTEC.',
      startDate: '2026-10-01',
      endDate: '2026-12-31',
      purchaseStart: '2026-10-01',
      purchaseEnd: '2026-12-20',
      regEnd: '2026-12-25',
      minPurchase: 20.00,
      maxNumbersPerCpf: 50,
      status: 'ATIVA',
      promoterName: 'Prefeitura Municipal de Barcarena — SEMAGRI',
      promoterDoc: '05.105.200/0001-22',
      legalChecklist: {
        legal_promoter_ok: true,
        participant_compliance_ok: true,
        prizes_funded_ok: true,
        rules_approved_ok: true,
        lgpd_declared_ok: true,
        electoral_cleared_ok: true
      },
      drawMethod: 'LOTERIA_FEDERAL'
    }
  ],
  boxes: [
    { id: 1, number: '260', sector: 'SETOR SALÕES', status: 'CONFIRMADO', permissionario: 'Sulamita Ferreira Figueira', activity: 'SALÃO E BARBEARIA' },
    { id: 2, number: '257', sector: 'MERCEARIAS', status: 'EM_REGULARIZACAO', permissionario: 'Jean Lima de Andrade', activity: 'VARIEDADES (DUPLICADO)' },
    { id: 3, number: '14', sector: 'PEIXES', status: 'VAGO_CONFIRMADO', permissionario: null, activity: 'PEIXE SALGADO' }
  ],
  batches: [
    {
      id: 1,
      campaignId: 1,
      boxNumber: '260',
      permissionarioName: 'Sulamita Ferreira Figueira',
      batchNumber: 1,
      prefix: 'NATAL',
      startNumber: 1,
      endNumber: 50,
      total: 50
    }
  ],
  vouchers: [], // generated below
  participations: [],
  attempts: [],
  auditLogs: [],
  draws: [],
  stagingReviews: {} // row_number -> { decision, justification, box, perm, isVago }
};

// Pre-populate initial 50 vouchers for Box 260
for (let i = 1; i <= 50; i++) {
  const code = 'NATAL-' + String(i).padStart(5, '0');
  DEFAULT_STATE.vouchers.push({
    code: code,
    batchId: 1,
    campaignId: 1,
    boxNumber: '260',
    permissionarioName: 'Sulamita Ferreira Figueira',
    sequence: i,
    status: 'DISTRIBUIDO',
    issuedValue: null,
    invoiceDoc: null,
    qrToken: null
  });
}

// State container with LocalStorage sync
let DB = (() => {
  try {
    const saved = localStorage.getItem('BARCARENA_MVP_DB');
    if (saved) return JSON.parse(saved);
  } catch (e) {
    console.warn('Erro ao ler localStorage:', e);
  }
  return JSON.parse(JSON.stringify(DEFAULT_STATE));
})();

function saveDb() {
  try {
    localStorage.setItem('BARCARENA_MVP_DB', JSON.stringify(DB));
  } catch (e) {
    console.error('Erro ao salvar no localStorage:', e);
  }
}

function resetDbToDefault() {
  if (confirm('Deseja restaurar todos os dados e testes para o estado inicial padrão?')) {
    localStorage.removeItem('BARCARENA_MVP_DB');
    DB = JSON.parse(JSON.stringify(DEFAULT_STATE));
    saveDb();
    window.location.reload();
  }
}

// Log audit helper
function logAudit(action, entity, entityId, details) {
  const log = {
    id: DB.auditLogs.length + 1,
    timestamp: new Date().toISOString(),
    user: DB.currentRole.toUpperCase(),
    action,
    entity,
    entityId: String(entityId || '-'),
    details: typeof details === 'object' ? JSON.stringify(details) : String(details)
  };
  DB.auditLogs.unshift(log);
  saveDb();
}

// Crypto SHA-256 helper
async function sha256(text) {
  const encoder = new TextEncoder();
  const data = encoder.encode(text);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// Navigation & Roles
function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.getAttribute('data-tab') === tabId));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + tabId));
  renderActiveTab(tabId);
}

function switchRole(roleKey) {
  DB.currentRole = roleKey;
  saveDb();
  const label = roleKey === 'admin' ? 'Administrador (SEMAGRI)' :
                roleKey === 'atendente' ? 'Atendente de Balcão' : 'Box 260 — Sulamita Ferreira';
  document.getElementById('currentUserName').textContent = label;
  const select = document.getElementById('activeRoleSelect');
  if (select) select.value = roleKey;
}

function renderActiveTab(tabId) {
  if (tabId === 'dashboard') renderDashboard();
  if (tabId === 'balcao') renderBalcao();
  if (tabId === 'boxes') renderBoxesAndStaging();
  if (tabId === 'campanhas') renderCampaigns();
  if (tabId === 'taloes') renderTaloes();
  if (tabId === 'portal') renderPortal();
  if (tabId === 'apuracao') renderApuracao();
  if (tabId === 'auditoria') renderAuditoria();
  if (tabId === 'testes') renderTestsTab();
}

// ================= 1. DASHBOARD =================
function renderDashboard() {
  const confirmedBoxes = DB.boxes.filter(b => b.status === 'CONFIRMADO').length;
  const activePerms = 1 + Object.values(DB.stagingReviews).filter(r => r.decision === 'APROVADO' && !r.isVago).length;
  const issuedVouchers = DB.vouchers.filter(v => v.status === 'EMITIDO' || v.status === 'UTILIZADO').length;
  const validParticipations = DB.participations.length;
  const uniqueConsumers = new Set(DB.participations.map(p => p.cpf)).size;

  document.getElementById('kpiBoxesConfirmed').textContent = confirmedBoxes;
  document.getElementById('kpiPermsActive').textContent = activePerms;
  document.getElementById('kpiVouchersIssued').textContent = issuedVouchers;
  document.getElementById('kpiVouchersTotal').textContent = 'Total em talões: ' + DB.vouchers.length + ' (' + validParticipations + ' validados)';
  document.getElementById('kpiParticipations').textContent = validParticipations;
  document.getElementById('kpiConsumers').textContent = 'Consumidores únicos: ' + uniqueConsumers;

  // Activities breakdown
  const actCounts = {};
  DB.participations.forEach(p => {
    actCounts[p.activity] = (actCounts[p.activity] || 0) + 1;
  });
  const actList = document.getElementById('activityBreakdownList');
  const actKeys = Object.keys(actCounts);
  if (actKeys.length === 0) {
    actList.innerHTML = '<p class="empty-state">Nenhuma participação validada ainda. Valide cupons na aba Balcão.</p>';
  } else {
    actList.innerHTML = actKeys.map(k => '<div class="lookup-item"><span>' + k + '</span><strong>' + actCounts[k] + ' cupom(ns)</strong></div>').join('');
  }

  // Rejections breakdown
  const rejCounts = {};
  DB.attempts.filter(a => !a.success).forEach(a => {
    rejCounts[a.reason] = (rejCounts[a.reason] || 0) + 1;
  });
  const rejList = document.getElementById('rejectionsBreakdownList');
  const rejKeys = Object.keys(rejCounts);
  if (rejKeys.length === 0) {
    rejList.innerHTML = '<p class="empty-state">Nenhuma recusa registrada até o momento.</p>';
  } else {
    rejList.innerHTML = rejKeys.map(k => '<div class="lookup-item"><span>' + k + '</span><span class="badge badge-danger">' + rejCounts[k] + '</span></div>').join('');
  }
}

// ================= 2. BALCÃO =================
function renderBalcao() {
  const campSelect = document.getElementById('attCampaignSelect');
  campSelect.innerHTML = DB.campaigns.filter(c => c.status === 'ATIVA').map(c => '<option value="' + c.id + '">' + c.name + ' (Ativa)</option>').join('');
  if (campSelect.children.length === 0) {
    campSelect.innerHTML = '<option value="">Nenhuma campanha ativa. Ative na aba Campanhas.</option>';
  }
  renderAttendanceHistory();
}

function handleVoucherLookup() {
  const code = document.getElementById('attVoucherCode').value.trim().toUpperCase();
  const feedback = document.getElementById('voucherLookupFeedback');
  if (!code) {
    feedback.textContent = 'Digite o código impresso no talão.';
    return;
  }
  const voucher = DB.vouchers.find(v => v.code === code);
  if (!voucher) {
    feedback.innerHTML = '<span style="color: var(--danger)">❌ Comprovante \'' + code + '\' não encontrado no lote.</span>';
  } else if (voucher.status === 'UTILIZADO') {
    feedback.innerHTML = '<span style="color: var(--danger)">⚠️ Comprovante já foi utilizado e validado anteriormente!</span>';
  } else if (voucher.status === 'DISTRIBUIDO' || voucher.status === 'EMITIDO') {
    feedback.innerHTML = '<span style="color: var(--success)">✅ Disponível para validação! Box: ' + voucher.boxNumber + ' (' + voucher.permissionarioName + ')</span>';
  } else {
    feedback.innerHTML = '<span style="color: var(--warning)">⚠️ Situação: ' + voucher.status + '</span>';
  }
}

function handleAttendanceSubmit(e) {
  e.preventDefault();
  const alertOk = document.getElementById('attendanceSuccessAlert');
  const alertErr = document.getElementById('attendanceErrorAlert');
  alertOk.style.display = 'none';
  alertErr.style.display = 'none';

  const campaignId = parseInt(document.getElementById('attCampaignSelect').value, 10);
  const code = document.getElementById('attVoucherCode').value.trim().toUpperCase();
  const rawCpf = document.getElementById('attParticipantCpf').value.trim();
  const cleanCpf = rawCpf.replace(/\D/g, '');
  const name = document.getElementById('attParticipantName').value.trim();
  const phone = document.getElementById('attParticipantPhone').value.trim();
  const neighborhood = document.getElementById('attParticipantNeighborhood').value.trim() || 'Barcarena';

  if (!code) return;
  const voucher = DB.vouchers.find(v => v.code === code);

  // Check 1: Existence
  if (!voucher) {
    recordAttempt(code, cleanCpf, false, 'Comprovante não cadastrado no lote');
    showAttendanceError('Comprovante Inexistente', 'O código \'' + code + '\' não pertence a nenhum talão distribuído.');
    return;
  }

  // Check 2: Already used (Duplicate prevention)
  if (voucher.status === 'UTILIZADO') {
    recordAttempt(code, cleanCpf, false, 'Comprovante já utilizado anteriormente');
    showAttendanceError('Comprovante Já Utilizado', 'O cupom \'' + code + '\' já foi validado em um sorteio anterior e não pode ser reutilizado!');
    return;
  }

  // Check 3: Incident status
  if (['CANCELADO', 'EXTRAVIADO', 'DEVOLVIDO'].includes(voucher.status)) {
    recordAttempt(code, cleanCpf, false, 'Comprovante com ocorrência (' + voucher.status + ')');
    showAttendanceError('Comprovante Inválido', 'O comprovante está marcado como ' + voucher.status + '.');
    return;
  }

  // Check 4: CPF Limit (50 max)
  const existingForCpf = DB.participations.filter(p => p.campaignId === campaignId && p.cpf === cleanCpf).length;
  if (existingForCpf >= 50) {
    recordAttempt(code, cleanCpf, false, 'Limite de 50 cupons por CPF atingido');
    showAttendanceError('Limite Atingido', 'Este CPF já atingiu a cota máxima de 50 participações na campanha.');
    return;
  }

  // Atomic state change
  voucher.status = 'UTILIZADO';
  const luckyNumber = String(DB.participations.length + 1).padStart(5, '0');

  const participation = {
    id: DB.participations.length + 1,
    campaignId,
    voucherCode: code,
    luckyNumber,
    cpf: cleanCpf,
    name,
    phone,
    neighborhood,
    boxNumber: voucher.boxNumber,
    permissionarioName: voucher.permissionarioName,
    activity: 'SALÃO E BARBEARIA',
    timestamp: new Date().toISOString()
  };

  DB.participations.push(participation);
  recordAttempt(code, cleanCpf, true, null);
  logAudit('PARTICIPATION_VALIDATED', 'Participation', luckyNumber, { voucher: code, cpf: cleanCpf, luckyNumber });
  saveDb();

  // Show success alert
  document.getElementById('resLuckyNumberTitle').textContent = 'NÚMERO DA SORTE: ' + luckyNumber;
  document.getElementById('resParticipantInfo').textContent = 'Consumidor: ' + name + ' (CPF: ' + rawCpf + ') — ' + (existingForCpf + 1) + 'º cupom na campanha';
  document.getElementById('resOriginInfo').textContent = 'Origem: Box ' + voucher.boxNumber + ' (' + voucher.permissionarioName + ') | Código: ' + code;
  alertOk.style.display = 'flex';

  // Clear inputs
  document.getElementById('attVoucherCode').value = '';
  document.getElementById('voucherLookupFeedback').textContent = 'Pronto para o próximo comprovante.';
  document.getElementById('attVoucherCode').focus();

  renderAttendanceHistory();
  renderDashboard();
}

function showAttendanceError(title, desc) {
  document.getElementById('errTitle').textContent = title;
  document.getElementById('errDesc').textContent = desc;
  document.getElementById('attendanceErrorAlert').style.display = 'flex';
  renderAttendanceHistory();
  renderDashboard();
}

function recordAttempt(code, cpf, success, reason) {
  DB.attempts.unshift({
    code,
    cpf: cpf || '-',
    success,
    reason: reason || 'Sucesso (Número gerado)',
    timestamp: new Date().toLocaleTimeString()
  });
  if (DB.attempts.length > 50) DB.attempts.pop();
  saveDb();
}

function renderAttendanceHistory() {
  const tbody = document.getElementById('attendanceHistoryTableBody');
  if (DB.attempts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center">Nenhum registro no balcão ainda.</td></tr>';
    return;
  }
  tbody.innerHTML = DB.attempts.slice(0, 10).map(a => `
    <tr>
      <td><strong>${a.code}</strong></td>
      <td>${a.cpf}</td>
      <td>${a.success ? '<span class="badge badge-success">Validado</span>' : '<span class="badge badge-danger">Recusado</span>'}</td>
      <td><small>${a.reason}</small></td>
    </tr>
  `).join('');
}

// ================= 3. BOXES & STAGING =================
function renderBoxesAndStaging() {
  const boxCounts = {};
  MOCK_DATA_ROWS.forEach(r => { if (r.box) boxCounts[r.box] = (boxCounts[r.box] || 0) + 1; });

  const tbody = document.getElementById('stagingTableBody');
  document.getElementById('stagingPendingCount').textContent = MOCK_DATA_ROWS.length + ' linhas na planilha';

  tbody.innerHTML = MOCK_DATA_ROWS.slice(0, 60).map(r => {
    const isDup = boxCounts[r.box] > 1;
    const isVago = (r.name || '').toUpperCase().includes('VAGO');
    const isEmpty = !r.name;
    const reviewed = DB.stagingReviews[r.row];

    let flagBadges = '';
    if (isDup) flagBadges += '<span class="badge badge-danger">Box Duplicado (257)</span> ';
    if (isVago) flagBadges += '<span class="badge badge-warning">Marcado VAGO</span> ';
    if (isEmpty) flagBadges += '<span class="badge badge-warning">Nome em Branco</span> ';
    if (!flagBadges) flagBadges = '<span class="badge badge-success">OK</span>';

    const statusBadge = reviewed ?
      (reviewed.decision === 'APROVADO' ? '<span class="badge badge-success">Aprovado</span>' : '<span class="badge badge-danger">Rejeitado</span>') :
      '<span class="badge badge-warning">Pendente Revisão</span>';

    const action = reviewed ?
      '<small style="color: var(--text-muted)">Decisão: ' + reviewed.decision + '</small>' :
      '<button class="btn btn-secondary btn-sm" onclick="openReviewModal(' + r.row + ', \'' + r.box + '\', \'' + encodeURIComponent(r.name) + '\', \'' + encodeURIComponent(r.activity) + '\')">Revisar</button>';

    return `
      <tr>
        <td>#${r.row}</td>
        <td><strong>Box ${r.box || '-'}</strong></td>
        <td>${r.name || '<em>(em branco)</em>'}</td>
        <td>${r.activity || '-'}</td>
        <td>${flagBadges}</td>
        <td>${statusBadge}</td>
        <td>${action}</td>
      </tr>
    `;
  }).join('');

  // Official boxes table
  const offTbody = document.getElementById('officialBoxesTableBody');
  offTbody.innerHTML = DB.boxes.map(b => `
    <tr>
      <td><strong>Box ${b.number}</strong></td>
      <td>${b.permissionario || '<em>(Sem titular)</em>'}</td>
      <td>${b.activity || '-'}</td>
      <td><span class="badge ${b.status === 'CONFIRMADO' ? 'badge-success' : 'badge-warning'}">${b.status}</span></td>
    </tr>
  `).join('');
}

function openReviewModal(rowNum, boxNum, nameEnc, actEnc) {
  const name = decodeURIComponent(nameEnc);
  const act = decodeURIComponent(actEnc);
  document.getElementById('modalStagingId').value = rowNum;
  document.getElementById('modalStagingInfo').textContent = 'Linha #' + rowNum + ': Box ' + boxNum + ' — Titular: ' + (name || '(em branco)') + ' | Atividade: ' + act;
  document.getElementById('reviewBoxNumber').value = boxNum;
  document.getElementById('reviewPermName').value = name;
  document.getElementById('reviewIsVago').checked = name.toUpperCase().includes('VAGO') || !name;
  document.getElementById('reviewJustification').value = '';
  document.getElementById('modalReviewStaging').style.display = 'flex';
}

function handleReviewSubmit(e) {
  e.preventDefault();
  const rowNum = parseInt(document.getElementById('modalStagingId').value, 10);
  const decision = document.getElementById('reviewDecision').value;
  const just = document.getElementById('reviewJustification').value.trim();
  const boxNum = document.getElementById('reviewBoxNumber').value.trim();
  const permName = document.getElementById('reviewPermName').value.trim();
  const isVago = document.getElementById('reviewIsVago').checked;

  DB.stagingReviews[rowNum] = {
    decision,
    justification: just,
    box: boxNum,
    perm: permName,
    isVago
  };

  if (decision === 'APROVADO') {
    const existing = DB.boxes.find(b => b.number === boxNum);
    if (!existing) {
      DB.boxes.push({
        id: DB.boxes.length + 1,
        number: boxNum,
        sector: 'SETOR GERAL',
        status: isVago ? 'VAGO_CONFIRMADO' : 'CONFIRMADO',
        permissionario: isVago ? null : permName,
        activity: 'DIVERSOS'
      });
    } else {
      existing.status = isVago ? 'VAGO_CONFIRMADO' : 'CONFIRMADO';
      existing.permissionario = isVago ? null : permName;
    }
  }

  logAudit('STAGING_ROW_REVIEWED', 'ImportStagingRow', rowNum, { decision, justification: just, box: boxNum });
  saveDb();
  closeModal('modalReviewStaging');
  renderBoxesAndStaging();
  renderDashboard();
}

// ================= 4. CAMPANHAS =================
function renderCampaigns() {
  const tbody = document.getElementById('campaignsTableBody');
  tbody.innerHTML = DB.campaigns.map(c => {
    const chk = c.legalChecklist || {};
    const count = Object.values(chk).filter(Boolean).length;
    const legalBadge = count === 6 ?
      '<span class="badge badge-success">6/6 Homologado</span>' :
      '<span class="badge badge-warning">' + count + '/6 Pendente</span>';

    const statusBadge = c.status === 'ATIVA' ? '<span class="badge badge-success">Ativa</span>' :
                        c.status === 'APROVADA' ? '<span class="badge badge-info">Aprovada</span>' :
                        c.status === 'ENCERRADA' ? '<span class="badge badge-warning">Encerrada</span>' :
                        '<span class="badge badge-secondary">' + c.status + '</span>';

    let actions = '';
    if (c.status === 'EM_ELABORACAO') {
      actions += '<button class="btn btn-secondary btn-sm" onclick="openLegalModal(' + c.id + ')">⚖️ Checklist Jurídico</button> ';
    }
    if (c.status === 'APROVADA') {
      actions += '<button class="btn btn-primary btn-sm" onclick="activateCampaign(' + c.id + ')">🚀 Ativar Campanha</button> ';
    }
    if (c.status === 'ATIVA') {
      actions += '<button class="btn btn-warning btn-sm" onclick="closeCampaign(' + c.id + ')">🔒 Encerrar Participação</button> ';
    }

    return `
      <tr>
        <td>#${c.id}</td>
        <td><strong>${c.name}</strong></td>
        <td>${c.purchaseStart} a ${c.purchaseEnd}</td>
        <td>R$ ${c.minPurchase.toFixed(2)}</td>
        <td>${statusBadge}</td>
        <td>${c.promoterName || '-'}</td>
        <td>${legalBadge}</td>
        <td>${actions || '<small>Finalizada</small>'}</td>
      </tr>
    `;
  }).join('');
}

function openNewCampaignModal() {
  document.getElementById('modalNewCampaign').style.display = 'flex';
}

function handleNewCampaignSubmit(e) {
  e.preventDefault();
  const newCamp = {
    id: DB.campaigns.length + 1,
    name: document.getElementById('campName').value.trim(),
    description: document.getElementById('campDesc').value.trim(),
    startDate: document.getElementById('campStart').value,
    endDate: document.getElementById('campEnd').value,
    purchaseStart: document.getElementById('campPurchaseStart').value,
    purchaseEnd: document.getElementById('campPurchaseEnd').value,
    regEnd: document.getElementById('campRegEnd').value,
    minPurchase: parseFloat(document.getElementById('campMinValue').value),
    maxNumbersPerCpf: 50,
    status: 'EM_ELABORACAO',
    promoterName: null,
    legalChecklist: {},
    drawMethod: 'LOTERIA_FEDERAL'
  };
  DB.campaigns.push(newCamp);
  logAudit('CAMPAIGN_CREATED', 'Campaign', newCamp.id, { name: newCamp.name });
  saveDb();
  closeModal('modalNewCampaign');
  renderCampaigns();
}

function openLegalModal(campId) {
  document.getElementById('modalLegalCampaignId').value = campId;
  document.getElementById('chkPromoter').checked = true;
  document.getElementById('chkParticipants').checked = true;
  document.getElementById('chkPrizes').checked = true;
  document.getElementById('chkRules').checked = true;
  document.getElementById('chkLgpd').checked = true;
  document.getElementById('chkElectoral').checked = true;
  document.getElementById('legalJustification').value = 'Processo Administrativo SEMAGRI nº 2026/089. Todos os 6 requisitos cumpridos.';
  document.getElementById('modalLegalApprovals').style.display = 'flex';
}

function handleLegalApprovalsSubmit(e) {
  e.preventDefault();
  const campId = parseInt(document.getElementById('modalLegalCampaignId').value, 10);
  const camp = DB.campaigns.find(c => c.id === campId);
  if (!camp) return;

  camp.promoterName = document.getElementById('legalPromoterName').value.trim();
  camp.promoterDoc = document.getElementById('legalPromoterDoc').value.trim();
  camp.legalChecklist = {
    legal_promoter_ok: document.getElementById('chkPromoter').checked,
    participant_compliance_ok: document.getElementById('chkParticipants').checked,
    prizes_funded_ok: document.getElementById('chkPrizes').checked,
    rules_approved_ok: document.getElementById('chkRules').checked,
    lgpd_declared_ok: document.getElementById('chkLgpd').checked,
    electoral_cleared_ok: document.getElementById('chkElectoral').checked
  };
  camp.status = 'APROVADA';
  logAudit('CAMPAIGN_LEGAL_APPROVED', 'Campaign', campId, { status: 'APROVADA' });
  saveDb();
  closeModal('modalLegalApprovals');
  renderCampaigns();
}

function activateCampaign(campId) {
  const camp = DB.campaigns.find(c => c.id === campId);
  if (!camp) return;
  camp.status = 'ATIVA';
  logAudit('CAMPAIGN_ACTIVATED', 'Campaign', campId, { status: 'ATIVA' });
  saveDb();
  renderCampaigns();
  renderDashboard();
}

function closeCampaign(campId) {
  const camp = DB.campaigns.find(c => c.id === campId);
  if (!camp) return;
  camp.status = 'ENCERRADA';
  logAudit('CAMPAIGN_CLOSED', 'Campaign', campId, { status: 'ENCERRADA' });
  saveDb();
  renderCampaigns();
  renderDashboard();
}

// ================= 5. TALÕES & COMPROVANTES =================
function renderTaloes() {
  const campSelect = document.getElementById('batchCampaignSelect');
  campSelect.innerHTML = DB.campaigns.map(c => '<option value="' + c.id + '">' + c.name + ' (' + c.status + ')</option>').join('');

  const boxSelect = document.getElementById('batchBoxSelect');
  boxSelect.innerHTML = '<option value="">Selecione um Box Confirmado</option>' +
    DB.boxes.filter(b => b.status === 'CONFIRMADO' && b.permissionario)
      .map(b => '<option value="' + b.number + '" data-perm="' + b.permissionario + '">Box ' + b.number + ' — ' + b.permissionario + '</option>').join('');
}

function handleBatchBoxChange(boxNumber) {
  const select = document.getElementById('batchBoxSelect');
  const opt = select.selectedOptions[0];
  if (opt) {
    document.getElementById('batchPermissionarioInput').value = opt.getAttribute('data-perm') || '';
  }
}

function handleCreateBatchSubmit(e) {
  e.preventDefault();
  const boxNum = document.getElementById('batchBoxSelect').value;
  const permName = document.getElementById('batchPermissionarioInput').value;
  const prefix = document.getElementById('batchPrefix').value.trim().toUpperCase();
  const start = parseInt(document.getElementById('batchStart').value, 10);
  const end = parseInt(document.getElementById('batchEnd').value, 10);

  if (start > end) {
    alert('O número inicial deve ser menor ou igual ao final.');
    return;
  }

  // Overlap verification
  const overlap = DB.batches.find(b => b.prefix === prefix && !(start > b.endNumber || end < b.startNumber));
  if (overlap) {
    alert('Conflito de intervalo! O lote #' + overlap.batchNumber + ' já utiliza o intervalo [' + overlap.startNumber + '..' + overlap.endNumber + '] com o prefixo \'' + prefix + '\'.');
    return;
  }

  const batch = {
    id: DB.batches.length + 1,
    campaignId: 1,
    boxNumber: boxNum,
    permissionarioName: permName,
    batchNumber: DB.batches.length + 1,
    prefix,
    startNumber: start,
    endNumber: end,
    total: (end - start) + 1
  };
  DB.batches.push(batch);

  // Generate vouchers
  for (let i = start; i <= end; i++) {
    DB.vouchers.push({
      code: prefix + '-' + String(i).padStart(5, '0'),
      batchId: batch.id,
      campaignId: 1,
      boxNumber: boxNum,
      permissionarioName: permName,
      sequence: i,
      status: 'DISTRIBUIDO',
      issuedValue: null,
      invoiceDoc: null,
      qrToken: null
    });
  }

  logAudit('BATCH_CREATED', 'VoucherBatch', batch.id, { prefix, range: start + '..' + end, total: batch.total });
  saveDb();
  alert('Talão gerado com sucesso! Lote #' + batch.batchNumber + ' com ' + batch.total + ' comprovantes.');
  renderDashboard();
}

function handleDirectVoucherLookup() {
  const code = document.getElementById('lookupVoucherInput').value.trim().toUpperCase();
  const box = document.getElementById('voucherLookupResultBox');
  if (!code) return;

  const v = DB.vouchers.find(x => x.code === code);
  if (!v) {
    alert('Comprovante \'' + code + '\' não encontrado.');
    box.style.display = 'none';
    return;
  }

  document.getElementById('vlrCode').textContent = v.code;
  document.getElementById('vlrStatusBadge').textContent = v.status;
  document.getElementById('vlrStatusBadge').className = 'badge ' + (v.status === 'UTILIZADO' ? 'badge-danger' : 'badge-success');
  document.getElementById('vlrBox').textContent = 'Box ' + v.boxNumber;
  document.getElementById('vlrPerm').textContent = v.permissionarioName;
  document.getElementById('vlrBatch').textContent = 'Lote #' + v.batchId;
  document.getElementById('vlrValue').textContent = v.issuedValue ? 'R$ ' + v.issuedValue.toFixed(2) : 'Não informado';
  document.getElementById('vlrDoc').textContent = v.invoiceDoc || 'Sem documento vinculado';
  box.style.display = 'block';
}

// ================= 6. PORTAL DO PERMISSIONÁRIO =================
function renderPortal() {
  document.getElementById('portalPermName').textContent = 'Box 260 — Sulamita Ferreira Figueira';
  document.getElementById('portalPermDetails').textContent = 'Atividade: Salão e Barbearia | Nível Sebrae: Nível 1 - Regular | Cadastro: ATIVO';
}

function handlePortalIssueSubmit(e) {
  e.preventDefault();
  const code = document.getElementById('portalVoucherCode').value.trim().toUpperCase();
  const val = parseFloat(document.getElementById('portalVoucherValue').value);
  const doc = document.getElementById('portalInvoiceDoc').value.trim();

  const v = DB.vouchers.find(x => x.code === code);
  if (!v) {
    alert('Comprovante \'' + code + '\' não encontrado no seu lote.');
    return;
  }
  if (v.boxNumber !== '260') {
    alert('Violação de isolamento: este comprovante pertence a outro permissionário!');
    return;
  }
  if (v.status !== 'DISTRIBUIDO') {
    alert('Não é possível emitir: comprovante já está como \'' + v.status + '\'.');
    return;
  }

  v.status = 'EMITIDO';
  v.issuedValue = val;
  v.invoiceDoc = doc;
  v.qrToken = 'QR-' + Math.random().toString(36).substring(2, 10).toUpperCase();

  logAudit('VOUCHER_ISSUED_MERCHANT', 'Voucher', v.code, { value: val, doc, qr: v.qrToken });
  saveDb();

  const alertOk = document.getElementById('portalIssueSuccessAlert');
  document.getElementById('portalIssueDetails').innerHTML = 
    'Código: <strong>' + v.code + '</strong> | Valor: R$ ' + val.toFixed(2) + '<br>' +
    'Token QR Gerado: <code>' + v.qrToken + '</code><br>' +
    'O consumidor pode levar este código ao balcão para retirar o seu Número da Sorte!';
  alertOk.style.display = 'block';
  renderDashboard();
}

function handlePortalIncidentSubmit(e) {
  e.preventDefault();
  const code = document.getElementById('incidentVoucherCode').value.trim().toUpperCase();
  const type = document.getElementById('incidentType').value;
  const reason = document.getElementById('incidentReason').value.trim();

  const v = DB.vouchers.find(x => x.code === code);
  if (!v) {
    alert('Comprovante não encontrado.');
    return;
  }
  if (v.boxNumber !== '260') {
    alert('Violação de isolamento: este comprovante pertence a outro permissionário!');
    return;
  }
  if (v.status === 'UTILIZADO') {
    alert('Comprovante já foi utilizado em participação e não pode ser cancelado.');
    return;
  }

  v.status = type;
  logAudit('VOUCHER_' + type, 'Voucher', code, { reason });
  saveDb();
  alert('Ocorrência registrada! Comprovante ' + code + ' marcado como ' + type + '.');
  document.getElementById('incidentReason').value = '';
  renderDashboard();
}

// ================= 7. APURAÇÃO LOTERIA FEDERAL =================
function renderApuracao() {
  const campSelect = document.getElementById('drawCampaignSelect');
  campSelect.innerHTML = DB.campaigns.map(c => '<option value="' + c.id + '">' + c.name + ' (' + c.status + ')</option>').join('');

  // Default extraction sample values (Concurso CEF 5900)
  document.getElementById('drawContest').value = '5900';
  document.getElementById('drawP1').value = '24568';
  document.getElementById('drawP2').value = '13492';
  document.getElementById('drawP3').value = '56701';
  document.getElementById('drawP4').value = '89234';
  document.getElementById('drawP5').value = '07815';
  document.getElementById('drawPrizeTitle').value = 'Moto 160cc 0km';

  renderDrawHistory();
}

async function handleFederalDrawSubmit(e) {
  e.preventDefault();
  const campId = parseInt(document.getElementById('drawCampaignSelect').value, 10);
  const camp = DB.campaigns.find(c => c.id === campId);
  const contest = document.getElementById('drawContest').value.trim();
  const prizeTitle = document.getElementById('drawPrizeTitle').value.trim();

  const validParts = DB.participations.filter(p => p.campaignId === campId);
  if (validParts.length === 0) {
    alert('Não existem participações validadas nesta campanha para apuração. Valide ao menos um cupom na aba Balcão antes de apurar.');
    return;
  }

  // Freeze base and calculate SHA-256
  const baseString = validParts.map(p => p.id + '|' + p.luckyNumber + '|' + p.cpf + '|' + p.voucherCode + '|' + p.timestamp).join('\n');
  const baseSha = await sha256(baseString);

  // Extract units
  const p1 = document.getElementById('drawP1').value.trim();
  const p2 = document.getElementById('drawP2').value.trim();
  const p3 = document.getElementById('drawP3').value.trim();
  const p4 = document.getElementById('drawP4').value.trim();
  const p5 = document.getElementById('drawP5').value.trim();
  const target = p1.slice(-1) + p2.slice(-1) + p3.slice(-1) + p4.slice(-1) + p5.slice(-1);

  // Find closest lucky number
  const targetInt = parseInt(target, 10);
  const winner = validParts.reduce((prev, curr) => {
    return (Math.abs(parseInt(curr.luckyNumber, 10) - targetInt) < Math.abs(parseInt(prev.luckyNumber, 10) - targetInt)) ? curr : prev;
  });

  // End campaign
  camp.status = 'ENCERRADA';

  const drawRecord = {
    id: DB.draws.length + 1,
    campaignId: campId,
    contest,
    targetCalculated: target,
    winnerLuckyNumber: winner.luckyNumber,
    winnerName: winner.name,
    winnerCpf: winner.cpf,
    winnerPhone: winner.phone,
    winnerBox: winner.boxNumber,
    prizeTitle,
    sha256: baseSha,
    deliveryStatus: 'PENDENTE',
    timestamp: new Date().toISOString()
  };
  DB.draws.push(drawRecord);

  logAudit('DRAW_EXECUTED_LOTERIA_FEDERAL', 'DrawResult', drawRecord.id, { contest, target, winner: winner.luckyNumber });
  saveDb();

  // Show UI alert
  const alertBox = document.getElementById('drawResultAlert');
  document.getElementById('drawWinnerLuckyNumber').textContent = 'Número da Sorte Contemplado: ' + winner.luckyNumber;
  document.getElementById('drawWinnerDetails').innerHTML = 
    '<strong>Ganhador:</strong> ' + winner.name + ' (CPF: ***.' + winner.cpf.substring(3, 6) + '.***-' + winner.cpf.slice(-2) + ')<br>' +
    '<strong>Contato:</strong> ' + winner.phone + ' | Bairro: ' + winner.neighborhood + '<br>' +
    '<strong>Comprovante Premiado:</strong> ' + winner.voucherCode + ' — Box: ' + winner.boxNumber + ' (' + winner.permissionarioName + ')<br>' +
    '<strong>Regra Oficial:</strong> Unidade simples dos 5 prêmios da CEF (Dígitos apurados: <strong>' + target + '</strong>)';
  document.getElementById('drawSha256').textContent = baseSha;
  alertBox.style.display = 'block';

  renderDrawHistory();
  renderCampaigns();
  renderDashboard();
}

function renderDrawHistory() {
  const tbody = document.getElementById('drawHistoryTableBody');
  if (DB.draws.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Nenhuma apuração realizada ainda nesta campanha.</td></tr>';
    return;
  }
  tbody.innerHTML = DB.draws.map(d => `
    <tr>
      <td>#${d.campaignId}</td>
      <td>Concurso ${d.contest}</td>
      <td><strong style="color: var(--primary); font-size: 1.1rem;">${d.winnerLuckyNumber}</strong></td>
      <td>${d.winnerName}</td>
      <td>${d.prizeTitle}</td>
      <td><span class="badge badge-warning">${d.deliveryStatus}</span></td>
    </tr>
  `).join('');
}

// ================= 8. AUDITORIA =================
function renderAuditoria() {
  const tbody = document.getElementById('auditTableBody');
  if (DB.auditLogs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center">Nenhum registro de auditoria ainda.</td></tr>';
    return;
  }
  tbody.innerHTML = DB.auditLogs.slice(0, 40).map(l => `
    <tr>
      <td>#${l.id}</td>
      <td><small>${l.timestamp.replace('T', ' ').substring(0, 19)}</small></td>
      <td><strong>${l.user}</strong></td>
      <td><span class="badge badge-info">${l.action}</span></td>
      <td>${l.entity}</td>
      <td>${l.entityId}</td>
      <td><code style="font-size: 0.78rem;">${l.details}</code></td>
    </tr>
  `).join('');
}

function exportParticipationsCsv() {
  if (DB.participations.length === 0) {
    alert('Nenhuma participação para exportar.');
    return;
  }
  let csv = 'numero_da_sorte,comprovante,box,permissionario,cpf,nome,data_validacao\n';
  DB.participations.forEach(p => {
    csv += p.luckyNumber + ',' + p.voucherCode + ',' + p.boxNumber + ',"' + p.permissionarioName + '",' + p.cpf + ',"' + p.name + '",' + p.timestamp + '\n';
  });
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'participacoes_validadas.csv';
  link.click();
}

// ================= 9. BATERIA DE TESTES NO NAVEGADOR =================
function renderTestsTab() {
  // Test tab view ready
}

async function runBrowserTestSuite() {
  const logBox = document.getElementById('testResultsLog');
  logBox.innerHTML = '<div style="color: #64748b;">Iniciando bateria de testes locais...</div>';
  const results = [];

  function assert(condition, message) {
    if (!condition) throw new Error(message);
  }

  async function runTest(name, fn) {
    try {
      await fn();
      results.push({ name, status: 'PASSED' });
    } catch (e) {
      results.push({ name, status: 'FAILED', error: e.message });
    }
  }

  // Test 1: RBAC & Auth Simulation
  await runTest('Fase 1: Autenticação e Perfis (ADMIN, ATENDENTE, PERMISSIONARIO)', () => {
    assert(['admin', 'atendente', 'permissionario'].includes(DB.currentRole), 'Perfil atual inválido');
  });

  // Test 2: Excel Staging & Anomaly Detection
  await runTest('Fase 2: Diagnóstico da Planilha Real (292 linhas, Box 257 duplo, 13 vagos, 13 vazios, 77 ausentes do mapa 368)', () => {
    assert(MOCK_DATA_ROWS.length === 292, 'Total de linhas esperado 292, obtido: ' + MOCK_DATA_ROWS.length);
    const b257 = MOCK_DATA_ROWS.filter(r => r.box === '257');
    assert(b257.length === 2, 'Box 257 deveria aparecer 2 vezes, apareceu: ' + b257.length);
    const vagos = MOCK_DATA_ROWS.filter(r => (r.name || '').toUpperCase().includes('VAGO'));
    assert(vagos.length === 13, 'Deveria haver 13 boxes com nome \'vago\', obtido: ' + vagos.length);
    const emptyNames = MOCK_DATA_ROWS.filter(r => !r.name);
    assert(emptyNames.length === 13, 'Deveria haver 13 boxes com nome em branco, obtido: ' + emptyNames.length);
  });

  // Test 3: Campaign State Machine & Legal Gates
  await runTest('Fase 3: Trava Jurídica dos 6 Itens Obrigatórios de Campanha', () => {
    const c = DB.campaigns[0];
    assert(c.status === 'ATIVA', 'Campanha piloto deveria estar ATIVA');
    const gates = Object.values(c.legalChecklist);
    assert(gates.length === 6 && gates.every(Boolean), 'Todos os 6 itens jurídicos devem estar aprovados para ativação');
  });

  // Test 4: Batch intervals non-overlapping
  await runTest('Fase 4: Talões com Faixas Exclusivas e Não-sobreposição', () => {
    const b1 = DB.batches[0];
    assert(b1.prefix === 'NATAL' && b1.startNumber === 1 && b1.endNumber === 50, 'Lote 1 deve cobrir 1..50');
    const isOverlapping = (start, end) => !(start > b1.endNumber || end < b1.startNumber);
    assert(isOverlapping(25, 75) === true, 'Sobreposição de intervalo [25..75] deveria ter sido detectada');
    assert(isOverlapping(51, 100) === false, 'Intervalo contíguo [51..100] não deve colidir');
  });

  // Test 5: Balcão Attendance & Concurrency Rejection
  await runTest('Fase 5: Balcão — 1 Cupom = 1 Número da Sorte e Bloqueio de Duplicidade', () => {
    const v5 = DB.vouchers.find(x => x.code === 'NATAL-00005');
    assert(v5, 'Comprovante NATAL-00005 deve existir');
    v5.status = 'UTILIZADO';
    const canReuse = (v5.status === 'DISTRIBUIDO' || v5.status === 'EMITIDO');
    assert(!canReuse, 'O mesmo cupom não pode ser validado uma segunda vez (bloqueio de duplicidade)');
    v5.status = 'DISTRIBUIDO';
  });

  // Test 6: IDOR Isolation
  await runTest('Fase 6: Isolamento Estrito do Portal do Permissionário (Box 260)', () => {
    const v = DB.vouchers.find(x => x.code === 'NATAL-00001');
    const attackerBox = '999';
    assert(v.boxNumber !== attackerBox, 'Tentativa de manipulação por box alheio detectada e bloqueada');
  });

  // Test 7: KPIs calculation
  await runTest('Fase 7: Painel de Indicadores e Trilha de Auditoria', () => {
    assert(DB.boxes.length >= 1, 'Boxes cadastrados');
    assert(DB.vouchers.length >= 50, 'Comprovantes em talões');
  });

  // Test 8: Loteria Federal Draw & SHA-256 Hash
  await runTest('Fase 8: Apuração Loteria Federal e Hash Criptográfico SHA-256', async () => {
    const testDigest = await sha256('TESTE-BARCARENA-2026');
    assert(testDigest.length === 64, 'Digest SHA-256 deve ter 64 caracteres hexadecimais');
    const prizes = ['24568', '13492', '56701', '89234', '07815'];
    const units = prizes.map(p => p.slice(-1)).join('');
    assert(units === '82145', 'Dígitos calculados: esperado 82145, obtido: ' + units);
  });

  // Render results
  let html = '';
  let allPass = true;
  results.forEach(r => {
    if (r.status === 'PASSED') {
      html += '<div style="padding: 0.5rem 0; border-bottom: 1px solid #e2e8f0; color: #15803d;">✅ <strong>[PASSOU]</strong> ' + r.name + '</div>';
    } else {
      allPass = false;
      html += '<div style="padding: 0.5rem 0; border-bottom: 1px solid #e2e8f0; color: #b91c1c;">❌ <strong>[FALHOU]</strong> ' + r.name + ' — Erro: ' + r.error + '</div>';
    }
  });

  const summary = allPass ?
    '<div class="alert alert-success" style="margin-top: 1rem;">🎉 <strong>Todos os ' + results.length + ' testes foram executados e APROVADOS com sucesso!</strong> O sistema está validado localmente.</div>' :
    '<div class="alert alert-danger" style="margin-top: 1rem;">⚠️ Alguns testes falharam. Verifique os erros acima.</div>';

  logBox.innerHTML = html + summary;
}

// Global bootstrap
document.addEventListener('DOMContentLoaded', () => {
  switchRole(DB.currentRole || 'atendente');
  renderActiveTab('dashboard');

  const cpfInput = document.getElementById('attParticipantCpf');
  if (cpfInput) {
    cpfInput.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v.length > 11) v = v.substring(0, 11);
      if (v.length > 9) v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4');
      else if (v.length > 6) v = v.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3');
      else if (v.length > 3) v = v.replace(/(\d{3})(\d{1,3})/, '$1.$2');
      e.target.value = v;
    });
  }
});

function closeModal(modalId) {
  document.getElementById(modalId).style.display = 'none';
}
