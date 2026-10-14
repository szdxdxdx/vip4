#include "CS_TrgtAtt_EIM.h"

void CS_Angle2CX_temp3(void *p, float64 Ctmp[3][3]);

void CS_TrgtAtt_EIMFun(void *p)
{

    CS_TrgtAtt_EIM *pIp = (CS_TrgtAtt_EIM*)p;
    float64 Cri[3][3];
    float64 Ctmp[3][3];
    float64 cw[3];

    /* Cro = Cbiasp * Angle2DCM (¦Õ_Trgt, ¦È_Trgt, ¦×_Trgt, Seq_AttD[WorkMode]); */
    CS_Angle2CX_temp3(pIp, Ctmp);
    
    MatrixMulti333(&pIp->csAttCoreData_Cro[0][0], &pIp->csAttCoreData_Cbiasp[0][0], &Ctmp[0][0]);

    /* Cri= Cro*Coi */
    MatrixMulti333(&Cri[0][0], &pIp->csAttCoreData_Cro[0][0], &pIp->csOrbData_coi[0][0]);

    /* qri=DCM2q(Cri) */
    C2Q(&pIp->csAttCoreData_qri[0], &Cri[0][0]);

    /*¦Øri = Cro*¦Øoi */
    MatrixMulti331(&pIp->csAttCoreData_wri[0], &pIp->csAttCoreData_Cro[0][0], &pIp->csOrbData_w0i[0]);

    /* ¦Øro = ¦Øri- Cro * ¦Øoi */
    MatrixMulti331(&cw[0], &pIp->csAttCoreData_Cro[0][0], &pIp->csOrbData_w0i[0]);

    pIp->csAttCoreData_wro[0] = pIp->csAttCoreData_wri[0] - cw[0];
    pIp->csAttCoreData_wro[1] = pIp->csAttCoreData_wri[1] - cw[1];
    pIp->csAttCoreData_wro[2] = pIp->csAttCoreData_wri[2] - cw[2];

    return;
}

void CS_Angle2CX_temp3(void *p, float64 Ctmp[3][3])
{
    CS_TrgtAtt_EIM *pIp = (CS_TrgtAtt_EIM*)p;
    switch(pIp->csAttPara_Seq_AttD[pIp->m_WorkMode])
    {
    case 123:
        Angle2C123(&Ctmp[0][0], pIp->csMnvData_A_Trgt[0], pIp->csMnvData_A_Trgt[1], pIp->csMnvData_A_Trgt[2]);
        break;
    case 132:
        Angle2C132(&Ctmp[0][0], pIp->csMnvData_A_Trgt[0], pIp->csMnvData_A_Trgt[1], pIp->csMnvData_A_Trgt[2]);
        break;
    case 213:
        Angle2C213(&Ctmp[0][0], pIp->csMnvData_A_Trgt[0], pIp->csMnvData_A_Trgt[1], pIp->csMnvData_A_Trgt[2]);
        break;
    case 231:
        Angle2C231(&Ctmp[0][0], pIp->csMnvData_A_Trgt[0], pIp->csMnvData_A_Trgt[1], pIp->csMnvData_A_Trgt[2]);
        break;
    case 312:
        Angle2C312(&Ctmp[0][0], pIp->csMnvData_A_Trgt[0], pIp->csMnvData_A_Trgt[1], pIp->csMnvData_A_Trgt[2]);
        break;
    case 321:
        Angle2C321(&Ctmp[0][0], pIp->csMnvData_A_Trgt[0], pIp->csMnvData_A_Trgt[1], pIp->csMnvData_A_Trgt[2]);
        break;
    default:
        Angle2C321(&Ctmp[0][0], pIp->csMnvData_A_Trgt[0], pIp->csMnvData_A_Trgt[1], pIp->csMnvData_A_Trgt[2]);
        break;
    }

    return;
}