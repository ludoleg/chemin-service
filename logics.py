#Where business logics reside.
import phaselist

class QuantModeModel:
        title = "Default"
        description = "Using the Rockforming DB"
        selected = phaselist.defaultPhases
        available = phaselist.availablePhases
        qlambda = 0
        qtarget = "Co"
        fwhma = -0.001348
        fwhmb = 0.352021
        inventory = "rockforming"

