document.addEventListener('DOMContentLoaded', function () {
	const inputs = document.querySelectorAll('.cgccfp');

	inputs.forEach(input => {
		input.addEventListener('input', function () {
			let value = this.value.replace(/\D/g, '');

			if (value.length <= 11) {
				// CPF: 000.000.000-00
				value = value
					.replace(/(\d{3})(\d)/, '$1.$2')
					.replace(/(\d{3})(\d)/, '$1.$2')
					.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
			} else {
				// CNPJ: 00.000.000/0000-00
				value = value
					.replace(/^(\d{2})(\d)/, '$1.$2')
					.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
					.replace(/\.(\d{3})(\d)/, '.$1/$2')
					.replace(/(\d{4})(\d)/, '$1-$2');
			}

			this.value = value;
		});
	});
});
