
function fixlink() {
	F=$(basename $1)
	unlink $F
	ln -s ../../../zlib/${F} .
}

fixlink inffixed.h 
fixlink inflate.c
fixlink inflate.h 
fixlink inftrees.c
fixlink inftrees.h
fixlink zconf.h
fixlink zlib.h
fixlink zutil.c
fixlink zutil.h


