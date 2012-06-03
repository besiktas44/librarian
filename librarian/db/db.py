import sqlite3
from librarian.models import Book, Sequence, Author
from librarian import app

class Database(object):
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = app.config['DATABASE']

    def __enter__(self):
        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
        return self

    def __exit__(self, type, value, traceback):
        self.db.close()

    def get_book_by_id(self, book_id):
        cursor = self.db.cursor()
        cursor.execute("SELECT book_id, book_title, annotation, sequence_id, sequence_number FROM book WHERE book_id = ?", (book_id,))
        book = cursor.fetchone()
        if not book:
            return None
        authors = []
        for book_author in cursor.execute("SELECT author_id FROM author_book WHERE book_id = ?", (book_id,)):
            authors += [self.get_author_by_id(book_author['author_id'])]
        genres = []
        for book_genre in cursor.execute("SELECT genre FROM book_genre WHERE book_id = ?", (book_id,)):
            genres += [book_genre['genre']]
        sequence = None
        if book['sequence_id']:
            cursor.execute("SELECT title FROM sequence WHERE sequence_id = ?", (book['sequence_id'],))
            sequence = Sequence(book['sequence_id'], cursor.fetchone()['title'])
        return Book(
            book_id=book['book_id'],
            title=book['book_title'], 
            authors=authors,
            annotation=book['annotation'],
            sequence=sequence,
            sequence_number=book['sequence_number'],
            genres=genres
        )

    def get_author_by_id(self, author_id):
        cursor = self.db.cursor()
        cursor.execute("SELECT author_id, first_name, last_name FROM author WHERE author_id = ?", (author_id,))
        author = cursor.fetchone()
        if not author:
            return None
        return Author(
            author_id=author['author_id'],
            first_name=author['first_name'],
            last_name=author['last_name'],
        )

    def get_books_by_author(self, author_id):
        cursor = self.db.cursor()
        books = []
        for author_book in cursor.execute("SELECT book_id FROM author_book WHERE author_id = ? ", (author_id,)):
            books += [self.get_book_by_id(author_book['book_id'])]
        return books

    def get_sequence_books(self, sequence_id):
        cursor = self.db.cursor()
        books = []
        for sequence_book in cursor.execute("SELECT book_id FROM book WHERE sequence_id = ?", (sequence_id,)):
            books += [self.get_book_by_id(sequence_book['book_id'])]
        return books

    def search_by_title(self, title, author_id=None):
        cursor = self.db.cursor()
        books = []
        title = title.lower()
        title = title.replace(' ', '%')
        title = '%' + title + '%'
        if author_id:
            for book in cursor.execute(
                    "SELECT book.book_id FROM book, author_book WHERE author_book.book_id=book.book_id and author_book.author_id = ? and book_title LIKE ?",
                    (author_id, title,)):
                books += [self.get_book_by_id(book['book_id'])]
        else:
            for book in cursor.execute("SELECT book_id FROM book WHERE book_title LIKE ?", (title,)):
                books += [self.get_book_by_id(book['book_id'])]
        return books

    def search_authors_starting_from(self, prefix):
        cursor = self.db.cursor()
        prefix = prefix.lower()
        prefix += '%'
        authors = []
        for author in cursor.execute("SELECT author_id FROM author WHERE last_name LIKE ?", (prefix,)):
            authors += [self.get_author_by_id(author['author_id'])]
        return authors

    def add_book(self, book):
        cursor = self.db.cursor()

        cursor.execute('select sequence_id from sequence where title=?', (book.sequence.title,))
        sequence_row = cursor.fetchone()
        if sequence_row:
            sequence_id = sequence_row['sequence_id']
        else:
            cursor.execute('insert into sequence (title) values(?)', (book.sequence.title,))
            sequence_id = cursor.lastrowid

        cursor.execute('insert into book values (:book_id, :title, :annotation, :sequence_id, :sequence_number)', {
            'book_id': book.book_id, 'title': book.title,
            'annotation': book.annotation, 'sequence_id': sequence_id,
            'sequence_number': book.sequence_number
        })

        #authors
        for author in book.authors:
            cursor.execute('select author_id from author where first_name=? and last_name=?', (author.first_name, author.last_name))
            author_row = cursor.fetchone()
            if author_row:
                author_id = author_row['author_id']
            else:
                cursor.execute('insert into author (first_name, last_name) values (?, ?)', (author.first_name, author.last_name))
                author_id = cursor.lastrowid
            cursor.execute('insert into author_book values(?, ?)', (author_id, book.book_id))

        for genre in book.genres:
            cursor.execute('insert into book_genre values(?, ?)', (book.book_id, genre))
        self.db.commit()

    def add_author(self, first_name, last_name):
        return Author(1, first_name, last_name)