# CDPS


   Python script to generate a virtual architecture with: LB (load balancer), C1 (client) and 1-5 Servers through two required elements: Image .qcow2 (named "cdps-vm-base-p3.qcow2") and .xml virtual machine configuration document (named "plantilla-vm-p3.xml"). Both have to be in the same repository the script.
  
  
  
  
  
   Created by Pacoard and Merinom







MANUAL
	--> Create:\n inicia el entorno, crea los ficheros. Se determina el numero de servidores a crear mediante:
	-f : desde fichero esterno
	-n : manualmente
	--> Start:\n inicia las maquinas virtuales y muestra sus consolas. Dos opciones de consola:
	-g : consola grafica
	-t : consola textual
	--> Stop:\n para las maquinas virtuales y cierra sus consolas. Posibilidad de añadir:
	-f: parada forzada
	--> Destroy:\n terminar el entorno, parando las maquinas virtuales y elimando los ficheros asociados
	--> Monitor:\n Monitoriza el entorno, aportardo información sobre todas las MV:
	 sin aportar parametro, se proporciona el estado de la/s MV
	-cpu : Valores estadisticos sobre la CPU
	-i : Informacion basica del dominio
	-only: Permite obtener informacion individual de una MV proporcionando dominio de la MV y parametro de consulta.
