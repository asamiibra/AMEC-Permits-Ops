#!/bin/sh
set -eu

LAB_PASSWORD_RW="${SMB_PASSWORD_RW:-proposalops_rw_dev}"
LAB_PASSWORD_RO="${SMB_PASSWORD_RO:-proposalops_ro_dev}"
LAB_PASSWORD_DENIED="${SMB_PASSWORD_DENIED:-proposalops_denied_dev}"
LAB_PASSWORD_OWNER="${SMB_PASSWORD_OWNER:-owner_test_dev}"
LAB_PASSWORD_BD="${SMB_PASSWORD_BD:-bd_test_dev}"
LAB_PASSWORD_ENGINEERING="${SMB_PASSWORD_ENGINEERING:-engineering_test_dev}"
LAB_PASSWORD_EXTERNAL_RO="${SMB_PASSWORD_EXTERNAL_RO:-external_ro_dev}"

addgroup --system proposalops >/dev/null 2>&1 || true
for user in proposalops_rw proposalops_ro proposalops_denied owner_test bd_test engineering_test external_ro; do
    adduser --system --no-create-home --ingroup proposalops "$user" >/dev/null 2>&1 || true
done

printf '%s\n' "$LAB_PASSWORD_RW" "$LAB_PASSWORD_RW" | smbpasswd -a -s proposalops_rw
printf '%s\n' "$LAB_PASSWORD_RO" "$LAB_PASSWORD_RO" | smbpasswd -a -s proposalops_ro
printf '%s\n' "$LAB_PASSWORD_DENIED" "$LAB_PASSWORD_DENIED" | smbpasswd -a -s proposalops_denied
printf '%s\n' "$LAB_PASSWORD_OWNER" "$LAB_PASSWORD_OWNER" | smbpasswd -a -s owner_test
printf '%s\n' "$LAB_PASSWORD_BD" "$LAB_PASSWORD_BD" | smbpasswd -a -s bd_test
printf '%s\n' "$LAB_PASSWORD_ENGINEERING" "$LAB_PASSWORD_ENGINEERING" | smbpasswd -a -s engineering_test
printf '%s\n' "$LAB_PASSWORD_EXTERNAL_RO" "$LAB_PASSWORD_EXTERNAL_RO" | smbpasswd -a -s external_ro

mkdir -p "/srv/shares/Services Provider" /srv/shares/ProposalOpsLab/proposalops /srv/shares/ProposalOpsManaged /srv/shares/OwnerExternal /srv/shares/Marketing /srv/shares/pro /srv/shares/Tenders /srv/shares/Supervision
chown -R root:proposalops /srv/shares
chmod -R 0770 /srv/shares
cp /etc/samba/smb.conf.template /etc/samba/smb.conf
testparm -s /etc/samba/smb.conf >/dev/null
exec smbd --foreground --no-process-group --debug-stdout --configfile=/etc/samba/smb.conf
