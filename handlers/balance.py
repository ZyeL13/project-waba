# handlers/balance.py
import db

async def handle_balance(user_id: str, args: list) -> str:
    """/saldo - Lihat saldo per akun"""
    rows = await db.fetch_all(
        """SELECT account_id,
                  SUM(debit) AS total_debit,
                  SUM(credit) AS total_credit
           FROM journal
           WHERE user_id = ?
           GROUP BY account_id""",
        (user_id,)
    )
    if not rows:
        return "📊 Belum ada transaksi. Mulai dengan /catat."

    lines = ["📊 *Saldo per Akun:*"]
    total_debit = total_credit = 0
    for r in rows:
        account = r['account_id'].upper()
        debit = r['total_debit'] or 0
        credit = r['total_credit'] or 0
        net = debit - credit
        total_debit += debit
        total_credit += credit
        if net > 0:
            lines.append(f"  {account:12} Rp{int(net):>12,}  (Debit)")
        elif net < 0:
            lines.append(f"  {account:12} Rp{int(abs(net)):>12,}  (Kredit)")
        else:
            lines.append(f"  {account:12} Rp         0")

    lines.append("  " + "─" * 36)
    lines.append(f"  Total Debit : Rp{int(total_debit):>12,}")
    lines.append(f"  Total Kredit: Rp{int(total_credit):>12,}")
    lines.append(f"  Status: {'✅ Balance' if total_debit == total_credit else '⚠️ Tidak balance'}")

    return "\n".join(lines)


async def handle_neraca(user_id: str, args: list) -> str:
    """/neraca - Laporan posisi keuangan (Aset = Liabilitas + Ekuitas)"""
    rows = await db.fetch_all(
        """SELECT a.type,
                  SUM(j.debit) AS total_debit,
                  SUM(j.credit) AS total_credit
           FROM journal j
           JOIN accounts a ON j.account_id = a.id
           WHERE j.user_id = ?
           GROUP BY a.type""",
        (user_id,)
    )
    if not rows:
        return "📊 Belum ada transaksi. Mulai dengan /catat."

    # Hitung saldo per tipe akun
    balances = {}
    for r in rows:
        acc_type = r['type']  # asset, liability, revenue, expense
        net = (r['total_debit'] or 0) - (r['total_credit'] or 0)
        # Konversi revenue/expense ke ekuitas (retained earnings)
        if acc_type in ('revenue', 'expense'):
            key = 'equity'
            balances[key] = balances.get(key, 0) + (-net)
        else:
            balances[acc_type] = balances.get(acc_type, 0) + net

    aset = balances.get('asset', 0)
    liabilitas = balances.get('liability', 0)
    ekuitas = balances.get('equity', 0)
    balanced = aset == (liabilitas + ekuitas)

    lines = [
        "📈 *Laporan Posisi Keuangan*",
        "",
        "  *ASET*",
        f"  {'' if aset >= 0 else '('}Rp{int(abs(aset)):>12,}{'' if aset >= 0 else ')'}",
        "",
        "  *KEWAJIBAN & EKUITAS*",
        f"  Liabilitas   Rp{int(abs(liabilitas)):>12,}",
        f"  Ekuitas      Rp{int(abs(ekuitas)):>12,}",
        f"  ──────────────────────────────",
        f"  Total K+E    Rp{int(abs(liabilitas + ekuitas)):>12,}",
        "",
        f"  Status: {'✅ Balance' if balanced else '⚠️ Tidak balance'}",
    ]

    return "\n".join(lines)
