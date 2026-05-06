import requests
from odoo import api, fields, models


class MilleSyncLog(models.Model):
    _name = 'pipinos.sync.log'
    _description = 'Log Sinkronisasi Data Mille'
    _order = 'waktu_sync desc'
    _rec_name = 'waktu_sync'

    waktu_sync = fields.Datetime(
        string='Waktu Sync', default=fields.Datetime.now, readonly=True
    )
    status = fields.Selection(
        [('sukses', 'Sukses'), ('gagal', 'Gagal')],
        string='Status',
        readonly=True,
    )
    pesan = fields.Text(string='Pesan', readonly=True)
    jumlah_pelanggan = fields.Integer(string='Jml Pelanggan', readonly=True)
    jumlah_loyalty = fields.Integer(string='Jml Loyalty', readonly=True)


class MilleSyncWizard(models.TransientModel):
    _name = 'pipinos.mille.sync'
    _description = 'Wizard Sinkronisasi Data ke Sistem Mille'

    mille_api_url = fields.Char(
        string='URL API Mille',
        required=True,
        default='http://localhost:8069/mille/sync',
    )
    hasil = fields.Text(string='Hasil', readonly=True)

    def action_sync(self):
        pelanggan = self.env['pipinos.pengunjung'].search([])
        loyalty = self.env['pipinos.loyalty.member'].search([])

        payload = {
            'pelanggan': [{
                'id_pelanggan': p.id_pengunjung,
                'nama_lengkap': p.nama_lengkap,
                'no_hp': p.no_hp or '',
                'usia': p.usia_input,
                'gender': p.gender_input or '',
            } for p in pelanggan],
            'loyalty': [{
                'id_loyalty': l.id_loyalty,
                'id_pelanggan': l.id_pengunjung.id_pengunjung,
                'total_poin': l.total_poin,
                'status_level': l.status_level or '',
            } for l in loyalty],
        }

        status = 'gagal'
        pesan = ''
        try:
            resp = requests.post(self.mille_api_url, json=payload, timeout=10)
            resp.raise_for_status()
            status = 'sukses'
            pesan = f'HTTP {resp.status_code}: {resp.text[:500]}'
        except Exception as e:
            pesan = str(e)[:500]

        self.env['pipinos.sync.log'].create({
            'status': status,
            'pesan': pesan,
            'jumlah_pelanggan': len(pelanggan),
            'jumlah_loyalty': len(loyalty),
        })

        self.hasil = f"[{status.upper()}] {pesan}"

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pipinos.mille.sync',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
