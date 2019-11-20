from eagle import models, fields, api, _
from datetime import date
import datetime

class parent_payment_report_wiz(models.TransientModel):
    _name = 'parent.payment.report.wiz'
    
    parent_id = fields.Many2one('res.partner', string="Parent Name" )
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(sring="Date To")
    invoice_ids = fields.Many2many('account.invoice', string="Invoices")
    voucher_ids = fields.Many2many('account.voucher', string="Vouchers")
    date_today = fields.Date(string="Todays Date")
    past_balance = fields.Float(string="Past balance")
    user = fields.Many2one('res.users', string="Current User")
#    running_balance_credit=fields.Float(string="Running balance after all creadit lines")
    current_running_balance=fields.Float(string="Current Running balance")
    total_credit_amount = fields.Float(string="Credit")
    total_debit_amount = fields.Float(string="Debit")

    _defaults = {'current_running_balance': 0.0}

    @api.multi
    def calc_current_running_balance(self, total, paid):
        self.current_running_balance = self.current_running_balance + total - paid
        return self.current_running_balance

    @api.multi
    def calc_credit(self, credit):
        if credit != 0.0:
            self.total_credit_amount += credit

    @api.multi
    def calc_debit(self, debit):
        if debit != 0.0:
            self.total_debit_amount += debit

    @api.multi
    def cal_total_balance(self,child,parent):
        total_balance = 0
        if len(child) > 0:
            for child_rec in child:
                total_balance += child_rec.credit
        if parent:
            total_balance += parent.credit
        return total_balance

    @api.multi
    def line_details(self, invoices, vouchers, from_date, to_date):
        invoice_voucher_list = []
        final_inv_vouch_list = []

        for inv in invoices:
            inv_date = datetime.datetime.strptime(inv.date_invoice, "%Y-%m-%d").strftime("%d/%m/%Y")
            invoice_voucher_list.append({'date': inv_date, 'object': 'account.invoice', 'rec_id': inv})

        for vouch in vouchers:
            vouch_date = datetime.datetime.strptime(vouch.date, "%Y-%m-%d").strftime("%d/%m/%Y")
            invoice_voucher_list.append({'date': vouch_date, 'object': 'account.voucher', 'rec_id': vouch})

        for data in invoice_voucher_list:
            if 'account.invoice' in data['object']:
                if data['rec_id'].type == 'out_refund':
                    for inv_line in data['rec_id'].invoice_line_ids:
                        final_inv_vouch_list.append({'date': data['date'],
                                                     'invoice_number': data['rec_id'].number,
                                                     'student_name': data['rec_id'].partner_id.name,
                                                     'description': inv_line.product_id.name,
                                                     'debit': 0.0,
                                                     'credit': inv_line.price_unit})
                        self.calc_credit(inv_line.price_unit)
                else:
                    for inv_line in data['rec_id'].invoice_line_ids:
                        final_inv_vouch_list.append({'date': data['date'],
                                                     'invoice_number': data['rec_id'].number,
                                                     'student_name': data['rec_id'].partner_id.name,
                                                     'description': inv_line.product_id.name,
                                                     'debit': inv_line.price_unit,
                                                     'credit': 0.0})
                        self.calc_debit(inv_line.price_unit)

                for pay_line in data['rec_id'].payment_ids:
                    pay_date = datetime.datetime.strptime(pay_line.date, "%Y-%m-%d").strftime("%d/%m/%Y")
                    flag = False
                    for move_line in pay_line.move_id.line_id:
                        if move_line.debit == 0.00 and move_line.credit == 0.00:
                            flag = True
                    if flag:
                        for move_line in pay_line.move_id.line_id:
                            if pay_line.date >= from_date and pay_line.date <= to_date:
                                final_inv_vouch_list.append({'date': pay_date,
                                                             'invoice_number': data['rec_id'].number,
                                                             'student_name': data['rec_id'].partner_id.name,
                                                             'description': pay_line.ref,
                                                             'debit': move_line.debit,
                                                             'credit': move_line.credit})
                                if move_line.debit != 0.00:
                                    self.calc_debit(move_line.debit)
                                if move_line.credit != 0.00:
                                    self.calc_credit(move_line.credit)

                    if not flag:
                        voucher = False
                        for move_line in pay_line.move_id.line_id:
                            if move_line.reconcile_ref and move_line.name:
                                voucher = True
                        if voucher:
                            continue
                        else:
                            if pay_line.date >= from_date and pay_line.date <= to_date:
                                final_inv_vouch_list.append({'date': pay_date,
                                                             'invoice_number': data['rec_id'].number,
                                                             'description': pay_line.ref,
                                                             'debit': 0.0,
                                                             'credit': pay_line.credit})
                                self.calc_credit(pay_line.credit)

            elif 'account.voucher' in data['object']:
                if len(data['rec_id'].line_cr_ids) == 0 or (len(data['rec_id'].line_cr_ids) != 0 and data['rec_id'].amount != 0.0):
                    if data['rec_id'].partner_id.is_student == True:
                        final_inv_vouch_list.append({'date': data['date'],
                                                     'invoice_number': 'Advance Payment',
                                                     'student_name': data['rec_id'].partner_id.name,
                                                     'description': data['rec_id'].number,
                                                     'debit': 0.0,
                                                     'credit': data['rec_id'].amount})
                    elif data['rec_id'].partner_id.is_parent == True:
                        final_inv_vouch_list.append({'date': data['date'],
                                                     'invoice_number': 'Advance Payment',
                                                     'student_name': '',
                                                     'description': data['rec_id'].number,
                                                     'debit': 0.0,
                                                     'credit': data['rec_id'].amount})
                    self.calc_credit(data['rec_id'].amount)
                    #code to add refund pdc entry on parent report
                    final_inv_vouch_list.append({'date': data['date'],
                                                 'invoice_number': 'Refund Advance Payment',
                                                 'student_name': '',
                                                 'description': data['rec_id'].number,
                                                 'credit': 0.0,
                                                 'debit': data['rec_id'].amount})
                    self.calc_debit(data['rec_id'].amount)
        final_inv_vouch_list.sort(key=lambda x: datetime.datetime.strptime(x['date'], '%d/%m/%Y'))
        return final_inv_vouch_list

    @api.multi
    def open_report(self):
        voucher_obj = self.env['account.voucher']
        invoice_obj = self.env['account.invoice']

        invoice_ids = []
        voucher_ids = []
        parent_vouchers = voucher_obj.search([('partner_id', '=', self.parent_id.id), ('state', '=', 'posted'), ('date', '>=', self.date_from), ('date', '<=', self.date_to)])
        if parent_vouchers:
            voucher_ids.append(parent_vouchers.id)
        for each1 in self.parent_id.chield1_ids.ids:
            invoices = invoice_obj.search([('partner_id', '=', each1), ('state', 'in', ['open', 'paid']), ('date_invoice', '>=', self.date_from), ('date_invoice', '<=', self.date_to)])
            vouchers = voucher_obj.search([('partner_id', '=', each1), ('state', '=', 'posted'), ('date', '>=', self.date_from), ('date', '<=', self.date_to)])
            for each in invoices:
                invoice_ids.append(each.id)
            for each in vouchers:
                voucher_ids.append(each.id)

        past_balance = 0.0
        move_line_ids = self.env['account.move.line'].search(['|', ('partner_id', '=', self.parent_id.id), ('partner_id', 'in', self.parent_id.chield1_ids.ids), ('date', '<', self.date_from), ('journal_id.type', '!=', 'situation'), '|', ('account_id.type', '=', 'receivable'), ('account_id.type', '=', 'payable')])
        for move_line in move_line_ids:
            if move_line.credit == 0.0 and move_line.debit == 0.0:
                continue
            elif move_line.credit != 0.0:
                past_balance -= move_line.credit
            elif move_line.debit != 0.0:
                past_balance += move_line.debit

        self.user = self._uid
        self.past_balance = past_balance
        self.invoice_ids = [(6, 0, invoice_ids)]
        self.voucher_ids = [(6, 0, voucher_ids)]
        self.date_today = date.today()
        
#        running_bal=0+self.past_balance
#        for each in self.invoice_ids:
#            for line in each.invoice_line:
#                running_bal=running_bal+line.price_subtotal
#           
#        self.running_balance_credit=running_bal   
      
        value = {
            'type': 'ir.actions.report.xml',
            'report_name': 'edsys_edu_fee.report_parent_payment',
            'datas': {
                'model': 'parent.payment.report.wiz',
                'id': self.id,
                'ids': [self.id],
                'report_type': 'pdf',
                'report_file': 'edsys_edu_fee.report_parent_payment'
            },
            'name': self.parent_id.parent1_id+'_ Payment'+' '+' Report' ,
            'nodestroy': True
        }
        return value
    
    @api.multi
    def send_parents_report(self):
        if self.parent_id:
            email = self.parent_id.email
            mail_obj=self.env['mail.mail']
            email_server=self.env['ir.mail_server']
            email_sender=email_server.search([])
            ir_model_data = self.env['ir.model.data']
            template_id = ir_model_data.get_object_reference('edsys_edu_fee', 'email_template_send_parent_report_by_email')[1]
            template_rec = self.env['mail.template'].browse(template_id)
            template_rec.write({'email_to' : email,'email_from':email_sender.smtp_user, 'email_cc': ''})
            template_rec.send_mail(self.id, force_send=True)

