document.addEventListener('DOMContentLoaded', function () {
    const tabelas = document.querySelectorAll('.table-filter');
  
    tabelas.forEach(tabela => {
      new simpleDatatables.DataTable(tabela, {
        perPageSelect: [[5, 5], [10, 10], [25, 25], [50, 50], ["Todos", 0]],
        // se quiser iniciar já mostrando todos:
        // perPage: 0,
        labels: {
          placeholder: "Buscar...",
          perPage: "registros por página",
          noRows: "Nenhum registro encontrado",
          info: "Mostrando {start} a {end} de {rows} registros",
          noResults: "Nenhum resultado encontrado"
        },
        firstLast: true,
        firstText: "Primeira",
        lastText: "Última",
        prevText: "Anterior",
        nextText: "Próxima"
      });
    });
  });