#!/usr/bin/env python

from datetime import date, datetime, timedelta
import sqlite3

from dateutil.parser import parse as du_parse
from mako.template import Template
from sqlalchemy import Column, ForeignKey, Integer, String, Date, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine


Base = declarative_base()
 
class Client(Base):
    __tablename__ = 'client'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    address = Column(String(250), nullable=True)
    pc = Column(String(250), nullable=True)
    city = Column(String(250), nullable=True)
    country = Column(String(250), nullable=True)
    email = Column(String(250), nullable=True)
    phone = Column(String(250), nullable=True)
    skype = Column(String(250), nullable=True)
    company_name = Column(String(250), nullable=True)
    company_address = Column(String(250), nullable=True)
    company_pc = Column(String(250), nullable=True)
    company_city = Column(String(250), nullable=True)
    vat_nr = Column(String(250), nullable=True)


class Provider(Base):
    __tablename__ = 'provider'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    address = Column(String(250), nullable=True)
    email = Column(String(250), nullable=True)
    phone = Column(String(250), nullable=True)
    vat_nr = Column(String(250), nullable=True)


class Contract(Base):
    __tablename__ = 'contract'
    id = Column(Integer, primary_key=True)
    external_id = Column(String(250), nullable=True)
    client_id = Column(Integer, ForeignKey('client.id'), nullable=False)
    client = relationship(Client)
    begin_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    budget = Column(Float, nullable=True)
    hourly_rate = Column(Float, nullable=True)
    detail = Column(String(5000), nullable=False)


class InvoiceReceived(Base):
    __tablename__ = 'invoice_received'
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey('provider.id'), nullable=False)
    person = relationship(Provider)
    provider_invoice_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    total = Column(Float, nullable=False)
    pre_tax = Column(Float, nullable=False)
    taxes = Column(Float, nullable=False)
    detail = Column(String(5000), nullable=True)
    currency = Column(String(250), nullable=True)
    settled = Column(Boolean, nullable=False, default=False)
    settled_date = Column(Date, nullable=True)


class InvoiceSent(Base):
    __tablename__ = 'invoice_sent'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('client.id'), nullable=False)
    client = relationship(Client)
    date = Column(Date, nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    total = Column(Float, nullable=False)
    pre_tax = Column(Float, nullable=False)
    taxes = Column(Float, nullable=False)
    detail = Column(String(5000), nullable=True)
    currency = Column(String(250), nullable=True)
    settled = Column(Boolean, nullable=False, default=False)
    settled_date = Column(Date, nullable=True)


class Task(Base):
    __tablename__ = 'task'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('client.id'), nullable=False)
    client = relationship(Client)
    contract_id = Column(Integer, ForeignKey('contract.id'), nullable=True)
    contract = relationship(Contract)
    invoice_id = Column(Integer, ForeignKey('invoice_sent.id'), nullable=False)
    invoice = relationship(InvoiceSent)
    date = Column(Date, nullable=False)
    time_amount = Column(Float, nullable=True)
    hourly_rate = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    detail = Column(String(5000), nullable=False)


def store_input(input_file, session):
    input_file = import_file(input_file)
    client_id = int(input_file.client_id)
    with session.begin():
        contract = None
        try:
            contract_id = int(input_file.contract_id)
            contract = session.query(Contract).filter(Contract.id==contract_id).first()
        except:
            pass
        currency = None
        try:
            currency = input_file.currency
        except:
            pass
        client = session.query(Client).filter(Client.id==client_id).first()
        date = date.today()
        total_price = sum([t['price'] for t in args.input.tasks])
        invoice = InvoiceSent(client_id=client_id, date=date, taxes=0,
                              total=total_price, pre_tax=total_price,
                              from_date=du_parse(args.input.from_date),
                              to_date=du_parse(input_file.to_date),
                              currency=currency)
        session.add(invoice)
        tasks = [Task(client_id=client_id, contract_id=contract_id,
                      invoice=invoice, date=du_parse(task['date']),
                      time_amount=task['time_amount'],
                      price=task['price'], detail=task['detail']
                      )
                 for task in input_file.tasks]
        session.add_all(tasks)
    return invoice, tasks, client, contract


def retrieve_invoice(invoice_id, session):
    invoice = session.query(InvoiceSent).filter(InvoiceSent.id==invoice_id).first()
    client = invoice.client
    tasks = session.query(Task).filter(Task.invoice_id==invoice_id).all()
    contract = tasks[0].contract
    return invoice, tasks, client, contract


if __name__ == '__main__':
    import argparse
    import os
    import sys
    
    from import_file import import_file

    parser = argparse.ArgumentParser(description='Creates a new invoice in the '
                                                 'database and generates the '
                                                 'PDFs to send to clients.')
    parser.add_argument('--input', dest='input', action='store',
                        help='Input file with the tasks performed.')
    parser.add_argument('--init', dest='init', action='store_const',
                        const=True, default=False,
                        help='Whether to initialize the database.'
                             'If the database exists already, '
                             'this operation has no effect.')
    parser.add_argument('--invoice_id', dest='invoice_id', action='store',
                        help='Use this number to generate the invoice instead '
                             'of using the input file')

    args = parser.parse_args()

    if args.input is None and args.invoice_id is None and not args.init:
        print 'Either --input, --invoice_id or --init must be provided.'
        sys.exit(1)

    if args.input is not None and args.invoice_id is not None:
        print '--input and --invoice_id cannot be used together.'
        sys.exit(1)

    if args.init and args.invoice_id is not None:
        print '--init and --invoice_id cannot be used together.'
        sys.exit(1)

    # Create an engine that stores data in the local directory's
    # sqlalchemy_example.db file.
    engine = create_engine('sqlite:///finances.db')

    if args.init and not os.path.exists('finances.db'):
        # Create all tables in the engine. This is equivalent to "Create Table"
        # statements in raw SQL.
        Base.metadata.create_all(engine)

    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine, autoflush=False)
    session = DBSession(autocommit=True)
    if args.input is not None:
        invoice, tasks, client, contract = store_input(args.input, session)            
    elif args.invoice_id is not None:
        invoice, tasks, client, contract = retrieve_invoice(args.invoice_id, session)            
    else:
        sys.exit()
            
    root = './Invoices - sent'
    mytemplate = Template(filename='%s/invoice_template_de.html'%root,
                          input_encoding='utf-8', output_encoding='utf-8',
                          encoding_errors='replace')
    invoice_file_name = '%s/invoice_%s_%s_de.html'%(root, client.id,
                                                    invoice.date.strftime('%Y-%m-%d'))

    invoice_file = mytemplate.render(client=client, tasks=tasks,
                                     invoice=invoice)
    with open(invoice_file_name, 'wb') as fp:
        fp.write(invoice_file)

    mytemplate = Template(filename='%s/invoice_template_en.html'%root,
                          input_encoding='utf-8', output_encoding='utf-8',
                          encoding_errors='replace')
    invoice_file_name = '%s/invoice_%s_%s_en.html'%(root, client.id,
                                                    invoice.date.strftime('%Y-%m-%d'))

    invoice_file = mytemplate.render(client=client, tasks=tasks,
                                     invoice=invoice)
    with open(invoice_file_name, 'wb') as fp:
        fp.write(invoice_file)

