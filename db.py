import sqlite3
import time

class db:
    def __init__(self):
        filename = 'vacancies.db'
        self.connection = sqlite3.connect(filename)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            """
            create table if not exists vacancy_list (
                id integer primary key autoincrement,
                vac_id integer,
                employer_id integer,
                timestamp integer,
                rank text
            )
            """
        )
        self.connection.commit()

    def check_new_vacancy(self, vac_id):
        """
        check_new_vacancy(self, vac_id) - проверка есть ли вакансия в базе 
        """
        self.cursor.execute(
            f"select * from vacancy_list where vac_id = '{vac_id}'"
        )
        result = self.cursor.fetchall()
        return len(result) == 0
            

    def check_new_employer(self, employer_id):
        """
        check_new_employer(self, employer_id) - проверка отправляли ли на этой неделе
        этому работодателю
        """
        self.cursor.execute(
            f"select timestamp from vacancy_list where employer_id = {employer_id}"
        )
        result = self.cursor.fetchall()
        new_employer = False
        if len(result) > 0:
            if max([i[0] for i in result]) < time.time() + 600_000:
                new_employer = True
        return new_employer

    def add_vacancy(self, values):
        """
        add_vacancy(self, values) - Добавление вакансии в базу
        values : ( vac_id, employer_id, timestamp, rank )
        """
        self.cursor.execute(
            f'insert into vacancy_list (vac_id, employer_id, timestamp, rank) values (?,?,?,?)',
            values
        )
        self.connection.commit()
