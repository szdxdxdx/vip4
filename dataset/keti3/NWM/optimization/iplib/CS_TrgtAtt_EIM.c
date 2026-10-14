#include "NWM.h"
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
    
    MatrixMulti333(&Cro[0][0], &Cbiasp[0][0], &Ctmp[0][0]);

    /* Cri= Cro*Coi */
    MatrixMulti333(&Cri[0][0], &Cro[0][0], &OrbOut.coi[0][0]);

    /* qri=DCM2q(Cri) */
    C2Q(&qri[0], &Cri[0][0]);

    /*¦Øri = Cro*¦Øoi */
    MatrixMulti331(&wri[0], &Cro[0][0], &woi[0]);

    /* ¦Øro = ¦Øri- Cro * ¦Øoi */
    MatrixMulti331(&cw[0], &Cro[0][0], &woi[0]);

    wro[0] = wri[0] - cw[0];
    wro[1] = wri[1] - cw[1];
    wro[2] = wri[2] - cw[2];

    return;
}

void CS_Angle2CX_temp3(void *p, float64 Ctmp[3][3])
{
    CS_TrgtAtt_EIM *pIp = (CS_TrgtAtt_EIM*)p;
    switch(Seq_AttD[WorkMode])
    {
    case 123:
        Angle2C123(&Ctmp[0][0], Atti_Trgt[0], Atti_Trgt[1], Atti_Trgt[2]);
        break;
    case 132:
        Angle2C132(&Ctmp[0][0], Atti_Trgt[0], Atti_Trgt[1], Atti_Trgt[2]);
        break;
    case 213:
        Angle2C213(&Ctmp[0][0], Atti_Trgt[0], Atti_Trgt[1], Atti_Trgt[2]);
        break;
    case 231:
        Angle2C231(&Ctmp[0][0], Atti_Trgt[0], Atti_Trgt[1], Atti_Trgt[2]);
        break;
    case 312:
        Angle2C312(&Ctmp[0][0], Atti_Trgt[0], Atti_Trgt[1], Atti_Trgt[2]);
        break;
    case 321:
        Angle2C321(&Ctmp[0][0], Atti_Trgt[0], Atti_Trgt[1], Atti_Trgt[2]);
        break;
    default:
        Angle2C321(&Ctmp[0][0], Atti_Trgt[0], Atti_Trgt[1], Atti_Trgt[2]);
        break;
    }

    return;
}