import csv

from ofxstatement import statement
from ofxstatement.plugin import Plugin
from ofxstatement.parser import CsvStatementParser

import locale

from pprint import pformat, pprint


class IngRoPlugin(Plugin):
	"""ING Romania Plugin
	"""

	def get_parser(self, filename):
		f = open(filename, 'r', encoding=self.settings.get("charset", "ISO-8859-2"))
		parser = IngRoParser(f)
		return parser


class IngRoParser(CsvStatementParser):
	date_format = "%d %B %Y"
	mappings = {
		'date': 0,
		'memo': 1,
		'amount': 2
	}
	currentRecord = {
		'date': '',
		'details': '',
		'amount': 0.0,
		'type': 'NONE'
	}

	def parse(self):
		stmt = super(IngRoParser, self).parse()
		statement.recalculate_balance(stmt)
		return stmt

	def split_records(self):
		reader = csv.reader(self.fin)
		next(reader, None)
		return reader

	def parse_record(self, line):
		(date, reserved1, reserved2, details, reserved3, debit_amount, credit_amount) = line
		# print(">>>>> date is: " + date)

		debit_amount = float(debit_amount.replace(".", "").replace(",", ".")) if debit_amount is not '' else 0.0
		credit_amount = float(
			credit_amount.replace(".", "").replace(",", ".")) if credit_amount is not '' else 0.0

		if debit_amount > 0:
			statement_amount = debit_amount
			statement_type = 'DEBIT'
		elif credit_amount > 0:
			statement_amount = credit_amount
			statement_type = 'CREDIT'
		else:
			statement_amount = 0.0
			statement_type = 'NONE'

		# Skip header
		if date == 'Data':
			# print("^^^^^ Skip header")
			return None

		# Here we could commit the previous transaction because:
		# 1. We either start a new transaction (date field is valid)
		# 2. We reached the end of the file (reserved1 field is valid, and date is None)
		# However, we might not have a previous transaction (this is the first), so check if there is
		# anything to commit at this point.

		if date is not '' and self.currentRecord['date'] is not '':
			# print("----> Output currentRecord" + pformat(self.currentRecord))
			locale.setlocale(locale.LC_ALL, 'ro_RO')
			statement_object = super(IngRoParser, self).parse_record([
				self.currentRecord['date'],
				self.currentRecord['details'],
				self.currentRecord['amount']
			])
			statement_object.trntype = self.currentRecord['type']
			self.currentRecord['date'] = ''
			self.currentRecord['details'] = ''
			self.currentRecord['amount'] = 0
			self.currentRecord['type'] = 'NONE'

			return statement_object

		if date is not '':
			# We started reading in a new record.
			# print("##### We started a new record")
			self.currentRecord['date'] = date
			self.currentRecord['details'] = details
			self.currentRecord['amount'] = statement_amount
			self.currentRecord['type'] = statement_type

		if reserved1 is not '':
			# We are at the end of the file where the bank/account manager signatures
			# are found in the reserved fields. This means that there's no current record to
			# commit.
			# print("----- We are at the end of the file")
			self.currentRecord['date'] = ''
			self.currentRecord['details'] = ''
			self.currentRecord['amount'] = 0
			self.currentRecord['type'] = 'NONE'

		if date is '':
			# This line contains extra details for the current transaction
			# print("***** Adding details ...")
			self.currentRecord['details'] = self.currentRecord['details'] + " " + details
