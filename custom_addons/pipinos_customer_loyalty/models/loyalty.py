from odoo import api, fields, models


class LoyaltyMember(models.Model):
    _name = 'pipinos.loyalty.member'
    _description = 'Status Poin Loyalty'
    _rec_name = 'id_pengunjung'

    id_loyalty = fields.Char(string='ID Loyalty', required=True, copy=False, readonly=True, default=lambda self: 'Baru')
    id_pengunjung = fields.Many2one('pipinos.pengunjung', string='pengunjung', required=True, ondelete='cascade')
    no_hp = fields.Char(string='No HP', related='id_pengunjung.no_hp', readonly=True)
    total_poin = fields.Integer(string='Total Poin')
    status_level = fields.Selection([
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ], string='Status Level', compute='_compute_status_level', store=True)
    reward_info = fields.Char(string='Info Reward', compute='_compute_reward_info', store=False)

    _sql_constraints = [
        ('unique_pengunjung_loyalty', 'unique(id_pengunjung)', 'pengunjung ini sudah terdaftar di sistem loyalty!')
    ]

    @api.depends('status_level', 'total_poin')
    def _compute_reward_info(self):
        today = fields.Date.today()
        kampanye_aktif = self.env['pipinos.kampanye'].search([
            ('tgl_mulai', '<=', today),
            ('tgl_selesai', '>=', today),
        ])
        level_labels = {'silver': 'Member Silver', 'gold': 'Member Gold', 'platinum': 'Member Platinum'}
        for rec in self:
            label = level_labels.get(rec.status_level, 'Member Silver')
            if kampanye_aktif:
                nama = ', '.join(kampanye_aktif.mapped('nama_kampanye'))
                rec.reward_info = f"{label} | Kampanye Aktif: {nama}"
            else:
                rec.reward_info = label

    @api.depends('total_poin')
    def _compute_status_level(self):
        level_configs = self.env['pipinos.loyalty.level.config'].search([('active', '=', True)], order='threshold_points asc')
        for rec in self:
            selected_level = 'silver'
            if level_configs:
                for config in level_configs:
                    if rec.total_poin >= config.threshold_points:
                        selected_level = config.level
            else:
                if rec.total_poin >= 300:
                    selected_level = 'platinum'
                elif rec.total_poin >= 100:
                    selected_level = 'gold'
                else:
                    selected_level = 'silver'
            rec.status_level = selected_level if selected_level in ('silver', 'gold', 'platinum') else 'silver'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('id_loyalty', 'Baru') == 'Baru':
                vals['id_loyalty'] = self.env['ir.sequence'].next_by_code('pipinos.loyalty.member') or 'Baru'
        return super().create(vals_list)

class LoyaltyLevelConfig(models.Model):
    _name = 'pipinos.loyalty.level.config'
    _description = 'Konfigurasi Status Level Loyalty'
    _rec_name = 'name'

    name = fields.Char(string='Nama Level', required=True)
    level = fields.Selection([
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ], string='Level', required=True, default='silver')
    threshold_points = fields.Integer(string='Threshold Poin', required=True)
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Catatan')

    def _trigger_loyalty_recompute(self):
        members = self.env['pipinos.loyalty.member'].search([])
        members.modified(['total_poin'])

    def write(self, vals):
        res = super().write(vals)
        self._trigger_loyalty_recompute()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._trigger_loyalty_recompute()
        return records

    def unlink(self):
        res = super().unlink()
        self.env['pipinos.loyalty.member'].search([]).modified(['total_poin'])
        return res


class PointConversionConfig(models.Model):
    _name = 'pipinos.point.conversion.config'
    _description = 'Konfigurasi Konversi Poin'
    _rec_name = 'name'

    name = fields.Char(string='Nama Konfigurasi', required=True, default='Default Konversi Poin')
    nominal_rupiah = fields.Integer(string='Nominal Rupiah', required=True, default=10000)
    point_value = fields.Integer(string='Poin Dihasilkan', required=True, default=1)
    active = fields.Boolean(string='Active', default=True)
