#include "NWM.h"
#include "CS_TrgtAtt_NWM_USU.h"

void CS_Angle2CX_temp1(void *p, float64 tmpCp[3][3], float64 a[3]);

void CS_TrgtAtt_NWM_USUFun(void *p)
{
    CS_TrgtAtt_NWM_USU *pIp = (CS_TrgtAtt_NWM_USU*)p;

    float64 tmpCp[3][3];
    float64 tmpCp_Trgtb[3][3];
    float64 tmpw[3];
    float64 a[3];
    float64 Cri[3][3];

    a[0] = 0.0;
    a[1] = 0.0;
    a[2] = psi_DA;

    /* tmpCp = Angle2DCM(0.0, 0.0, _DA, Seq_AttD[WorkMode]) */
    CS_Angle2CX_temp1(pIp, tmpCp, a);

    MatrixMulti333(&tmpCp_Trgtb[0][0], &Cbsi_DARot[0][0], &Cbiasp[0][0]);
    MatrixMulti333(&Cro_si[0][0], &tmpCp[0][0], &tmpCp_Trgtb[0][0]);

    MatrixMulti331(&tmpw[0], &Cro_si[0][0], &woi[0]);
    wri_si[0] = tmpw[0];
    wri_si[1] = tmpw[1];
    wri_si[2] = tmpw[2] + dpsi_DA;

    MatrixMulti333(&Cro[0][0], &Cbsi_DARot[0][0], &Cro_si[0][0]);
    MatrixMulti331(&wri[0], &Cbsi_DARot[0][0], &wri_si[0]);
    C2Angle123(&A_Ref_si[0], &Cro_si[0][0]);
    MatrixMulti333(&Cri[0][0], &Cro[0][0], &OrbOut.coi[0][0]); /* Cri= Cro*Coi */
    C2Q(&qri[0], &Cri[0][0]);                                     /* qri=DCM2q(Cri) */

    MatrixMulti331(&tmpw[0], &Cro[0][0], &woi[0]);

    wro[0] = wri[0] - tmpw[0];
    wro[1] = wri[1] - tmpw[1];
    wro[2] = wri[2] - tmpw[2];

    return;
}


void CS_Angle2CX_temp1(void *p, float64 tmpCp[3][3], float64 a[3])
{
    CS_TrgtAtt_NWM_USU *pIp = (CS_TrgtAtt_NWM_USU*)p;

    switch(Seq_AttD[WorkMode])
    {
    case 123:
        Angle2C123(&tmpCp[0][0], a[0], a[1], a[2]);
        break;
    case 132:
        Angle2C132(&tmpCp[0][0], a[0], a[1], a[2]);
        break;
    case 213:
        Angle2C213(&tmpCp[0][0], a[0], a[1], a[2]);
        break;
    case 231:
        Angle2C231(&tmpCp[0][0], a[0], a[1], a[2]);
        break;
    case 312:
        Angle2C312(&tmpCp[0][0], a[0], a[1], a[2]);
        break;
    case 321:
        Angle2C321(&tmpCp[0][0], a[0], a[1], a[2]);
        break;
    default:
        Angle2C321(&tmpCp[0][0], a[0], a[1], a[2]);
        break;
    }

    return;
}