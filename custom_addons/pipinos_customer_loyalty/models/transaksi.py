from odoo import api, fields, models

class Transaksi(models.Model):
    _name = 'pipinos.transaksi'
    _description = 'Data Pembelian'
    _rec_name = 'id_transaksi'

    id_transaksi = fields.Char(string='ID Transaksi', required=True, copy=False, readonly=True, default=lambda self: 'Baru')
    id_pengunjung = fields.Many2one('pipinos.pengunjung', string='pengunjung (FK)')
    tanggal = fields.Datetime(string='Tanggal Transaksi', default=fields.Datetime.now)
    detail_ids = fields.One2many('pipinos.detail.transaksi', 'id_transaksi', string='Rincian Menu')
    total_nominal = fields.Float(string='Total Nominal', compute='_compute_total_nominal', store=True, readonly=False)

    @api.depends('detail_ids.subtotal')
    def _compute_total_nominal(self):
        for rec in self:
            rec.total_nominal = sum(rec.detail_ids.mapped('subtotal'))

    def _auto_update_loyalty_points(self):
        config = self.env['pipinos.point.conversion.config'].search(
            [('active', '=', True)], limit=1, order='id desc'
        )
        if not config or config.nominal_rupiah <= 0 or not self.id_pengunjung:
            return
        poin = int(self.total_nominal / config.nominal_rupiah) * config.point_value
        if poin <= 0:
            return
        loyalty = self.env['pipinos.loyalty.member'].search(
            [('id_pengunjung', '=', self.id_pengunjung.id)], limit=1
        )
        if loyalty:
            loyalty.total_poin += poin
        else:
            self.env['pipinos.loyalty.member'].create({
                'id_pengunjung': self.id_pengunjung.id,
                'total_poin': poin,
            })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('id_transaksi', 'Baru') == 'Baru':
                vals['id_transaksi'] = self.env['ir.sequence'].next_by_code('pipinos.transaksi') or 'Baru'
        records = super().create(vals_list)
        for record in records:
            record._auto_update_loyalty_points()
        return records


class DetailTransaksi(models.Model):
    _name = 'pipinos.detail.transaksi'
    _description = 'Rincian Menu'

    id_detail = fields.Char(string='ID Detail', required=True, copy=False, readonly=True, default=lambda self: 'Baru')
    id_transaksi = fields.Many2one('pipinos.transaksi', string='Transaksi (FK)')
    id_pengunjung = fields.Many2one('pipinos.pengunjung', string='pengunjung (FK)', related='id_transaksi.id_pengunjung', store=True, readonly=True)
    id_menu = fields.Many2one('pipinos.item.menu', string='Menu (FK)')
    qty = fields.Integer(string='Qty')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True, readonly=False)

    @api.depends('id_menu', 'qty')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = (rec.id_menu.harga or 0.0) * (rec.qty or 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('id_detail', 'Baru') == 'Baru':
                vals['id_detail'] = self.env['ir.sequence'].next_by_code('pipinos.detail.transaksi') or 'Baru'
        return super().create(vals_list)


class ItemMenu(models.Model):
    _name = 'pipinos.item.menu'
    _description = 'Data Menu'
    _rec_name = 'nama_menu'

    id_menu = fields.Char(string='ID Menu', required=True, copy=False, readonly=True, default=lambda self: 'Baru')
    nama_menu = fields.Char(string='Nama Menu', required=True)
    harga = fields.Float(string='Harga')
    kategori = fields.Char(string='Kategori')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('id_menu', 'Baru') == 'Baru':
                vals['id_menu'] = self.env['ir.sequence'].next_by_code('pipinos.item.menu') or 'Baru'
        return super().create(vals_list)
